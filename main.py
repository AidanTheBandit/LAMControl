import os
import json
import logging
import coloredlogs
import threading
import time
from datetime import datetime, timezone
from integrations import lam_at_home
from utils import config, get_env, rabbit_hole, splash_screen, ui, llm_parse, task_executor, journal, web_server
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


def process_utterance(prompt_data, journal: journal.Journal, playwright_context):
    """Process a prompt/utterance and execute the corresponding task"""
    if isinstance(prompt_data, str):
        utterance = prompt_data
        prompt_id = None
        source = "direct"
    elif isinstance(prompt_data, dict):
        utterance = prompt_data.get('prompt', '')
        prompt_id = prompt_data.get('id')
        source = prompt_data.get('source', 'unknown')
    else: 
        utterance = prompt_data['utterance']['prompt']
        prompt_id = prompt_data.get('_id')
        source = "rabbit"
    
    logging.info(f"Processing prompt from {source}: {utterance}")

    entry, promptParsed = None, None
    response = None
    error = None
    
    try:
        if utterance:
            # split prompt into tasks
            promptParsed = llm_parse.LLMParse(utterance, journal.get_interactions())
            tasks = promptParsed.split("&&")

            # iterate through tasks and execute each sequentially
            task_responses = []
            for task in tasks:
                if task != "x":
                    logging.info(f"Executing task: {task}")
                    task_response = task_executor.execute_task(playwright_context, task)
                    if task_response:
                        task_responses.append(task_response)
            
            response = "; ".join(task_responses) if task_responses else "Task completed successfully"
        else:
            logging.info("No prompt found in entry, skipping LLM Parse and task execution.")
            error = "Empty prompt received"

        # Append the completed interaction to the journal
        entry = journal.add_entry(prompt_data if not isinstance(prompt_data, str) else utterance, llm_response=promptParsed)

        if config.config['lamathomesave_isenabled'] and entry and entry.type in config.config['lamathomesave_types']:
            lam_at_home.save(journal, entry)

    except PlaywrightTimeoutError as e:
        error = f"Playwright timeout: {str(e)}"
        logging.error(f"Playwright timed out while processing prompt: {e}")

    except Exception as e:
        error = f"Processing error: {str(e)}"
        logging.error(f"An error occurred while processing prompt: {e}")

    return {
        'prompt_id': prompt_id,
        'response': response,
        'error': error,
        'success': error is None
    }


def run_web_mode():
    """Run LAMControl in web server mode"""
    # Initialize journal for storing rolling transcript
    userJournal = journal.Journal(max_entries=config.config['rolling_transcript_size'])
    
    # Create web server instance - use enhanced version
    from utils import web_server_enhanced
    server = web_server_enhanced.LAMWebServer(
        host=config.config.get('web_server_host', '0.0.0.0'),
        port=config.config.get('web_server_port', 5000)
    )
    logging.info("Using enhanced web server with real-time updates")
    
    # Initialize Playwright context in main thread
    with sync_playwright() as p:
        # Use firefox in headless mode for server environments
        browser = p.firefox.launch(headless=True)
        state_file = os.path.join(config.config['cache_dir'], config.config['state_file'])
        context = browser.new_context(storage_state=state_file)
        
        # Define the prompt processing function for the server thread
        def process_prompts():
            while True:
                try:
                    if server.has_pending_prompts():
                        prompt_data = server.get_next_prompt()
                        if prompt_data:
                            result = process_utterance(prompt_data, userJournal, context)
                            
                            # Mark prompt as completed with response/error
                            if hasattr(server, 'mark_prompt_completed'):
                                server.mark_prompt_completed(
                                    result['prompt_id'], 
                                    response=result['response'], 
                                    error=result['error']
                                )
                    else:
                        # Sleep briefly when no prompts are pending
                        time.sleep(0.5)
                        
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logging.error(f"Error in prompt processing loop: {e}")
                    time.sleep(1)
        
        # Start prompt processing in a separate thread
        prompt_thread = threading.Thread(target=process_prompts)
        prompt_thread.daemon = True
        prompt_thread.start()
        
        logging.info("Web server starting. Waiting for prompts...")
        logging.info(f"Access the admin dashboard at: http://localhost:{config.config.get('web_server_port', 5000)}")
        
        # Start the web server (this will block the main thread)
        try:
            server.run(debug=config.config.get('debug', False))
        except KeyboardInterrupt:
            logging.info("Web server stopped by user")
        except Exception as e:
            logging.error(f"Web server error: {e}")
            raise


def main():
    try:
        # Check if only GROQ API key is needed for web mode
        if config.config["mode"] == "web":
            # For web mode, we only need GROQ API key
            if not get_env.GROQ_API_KEY:
                logging.error("GROQ API Key is required for web mode. Please set it in .env file.")
                if not os.path.exists(config.config["env_file"]):
                    ui.create_ui()
                return
        else:
            # For other modes, check if env file exists
            if not os.path.exists(config.config["env_file"]):
                ui.create_ui()
                
        print(splash_screen.colored_splash)
        logging.info("LAMControl is starting...")

        # create cache directory if it doesn't exist
        if not os.path.exists(config.config['cache_dir']):
            os.makedirs(config.config['cache_dir'])

        # Ensure state.json exists and is valid
        state_file = os.path.join(config.config['cache_dir'], config.config['state_file'])
        if not os.path.exists(state_file) or os.stat(state_file).st_size == 0:
            with open(state_file, 'w') as f:
                json.dump({}, f)

        if config.config["mode"] == "web":
            logging.info("Starting web mode...")
            run_web_mode()
            
        elif config.config["mode"] == "rabbit":
            # Initialize journal for storing rolling transcript
            userJournal = journal.Journal(max_entries=config.config['rolling_transcript_size'])
            
            with sync_playwright() as p:
                # Use firefox for full headless
                browser = p.firefox.launch(headless=False)
                context = browser.new_context(storage_state=state_file)  # Use state to stay logged in

                user, assistant = None, None
                if get_env.RH_ACCESS_TOKEN:
                    # fetch rabbit hole user profile
                    profile = rabbit_hole.fetch_user_profile()
                    user = profile.get('name')
                    assistant = profile.get('assistantName')
                
                currentTimeIso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                logging.info(f"Welcome {user}! LAMatHome is now listening for journal entries posted by {assistant}")
                for journal_entry in rabbit_hole.journal_entries_generator(currentTimeIso):
                    process_utterance(journal_entry, userJournal, context)
            
        elif config.config["mode"] == "cli":
            # Initialize journal for storing rolling transcript
            userJournal = journal.Journal(max_entries=config.config['rolling_transcript_size'])
            
            with sync_playwright() as p:
                # Use firefox for full headless
                browser = p.firefox.launch(headless=False)
                context = browser.new_context(storage_state=state_file)  # Use state to stay logged in

                user, assistant = None, None
                if get_env.RH_ACCESS_TOKEN:
                    # fetch rabbit hole user profile
                    profile = rabbit_hole.fetch_user_profile()
                    if profile:
                        user = profile.get('name')
                        assistant = profile.get('assistantName')
                
                logging.info("Entering interactive mode...")
                while True:
                    user_input = input(f"{user}@LAMControl> " if user else "LAMControl> ")
                    result = process_utterance(user_input, userJournal, context)

        else:
            logging.error("Invalid mode specified in config.json. Valid modes: web, rabbit, cli")

    except KeyboardInterrupt:
        print("\n")
        logging.info("Program terminated by user")
    except Exception as e:
        logging.error(f"Unexpected error in main(): {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        logging.info("LAMControl shutting down...")
        lam_at_home.terminate()


if __name__ == "__main__":
    # configure logging and run LAMatHome
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    coloredlogs.install(
        level='INFO', 
        fmt='%(asctime)s - %(levelname)s - %(message)s', 
        datefmt='%Y-%m-%d %H:%M:%S', 
        field_styles={'asctime': {'color': 'white'}}
    )
    main()
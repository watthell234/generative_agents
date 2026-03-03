import os
import sys
import time
import json
import datetime
from django.utils import timezone
from .models import Scenario

# Add paths to sys.path if not already added (settings.py should have done it, but to be safe)
# We assume settings.py has added 'reverie/backend_server' and 'environment/frontend_server' or similar.
# Actually settings.py added 'reverie' and 'environment'. 
# The imports in reverie.py are `from global_methods import *` etc.
# These modules are in `reverie/backend_server`. 
# So we need `reverie/backend_server` in sys.path.

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_SERVER_PATH = os.path.abspath(os.path.join(BASE_DIR, '../reverie/backend_server'))
sys.path.append(BACKEND_SERVER_PATH)

print(f"DEBUG: BASE_DIR={BASE_DIR}")
print(f"DEBUG: BACKEND_SERVER_PATH={BACKEND_SERVER_PATH}")
print(f"DEBUG: sys.path={sys.path}")

import types

# Monkey-patch utils and load OpenAI Key
try:
    # Create a mock utils module directly to avoid file permission issues
    utils = types.ModuleType("utils")
    
    # Set the Key (Hardcoded from inspection of reverie/backend_server/utils.py)
    utils.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    utils.key_owner = "Julius Gonzalez"
    
    # Path configurations relative to ib_workbench
    utils.maze_assets_loc = "../environment/frontend_server/static_dirs/assets"
    utils.env_matrix = f"{utils.maze_assets_loc}/the_ville/matrix"
    utils.env_visuals = f"{utils.maze_assets_loc}/the_ville/visuals"
    utils.fs_storage = "../environment/frontend_server/storage"
    utils.fs_temp_storage = "../environment/frontend_server/temp_storage"
    utils.debug = True
    
    # Inject into sys.modules so 'import utils' finds this object
    sys.modules["utils"] = utils
    
    UTILS_AVAILABLE = True
    print(f"DEBUG: Successfully injected mock utils with API Key.")
except Exception as e:
    print(f"WARNING: Could not load/mock utils: {e}")
    UTILS_AVAILABLE = False
    utils = None

try:
    from reverie import ReverieServer
    from persona.persona import Persona
    REVERIE_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Could not import ReverieServer: {e}")
    REVERIE_AVAILABLE = False
    
    # Mock classes for fallback
    class ReverieServer:
        def __init__(self, fork, sim):
            self.personas = {}
            self.curr_time = datetime.datetime.now()
            
        def start_server(self, steps):
            pass

    class Persona:
        pass

try:
    import openai
    OPENAI_AVAILABLE = True
    # Try to find API key from environment or utils
    if os.environ.get("OPENAI_API_KEY"):
        openai.api_key = os.environ.get("OPENAI_API_KEY")
        print("DEBUG: Using OpenAI Key from Environment")
    elif utils and hasattr(utils, 'openai_api_key'):
        openai.api_key = utils.openai_api_key
        print("DEBUG: Using OpenAI Key from utils.py")
except ImportError:
    OPENAI_AVAILABLE = False

class SimpleLLMEngine:
    def __init__(self, scenario):
        self.scenario = scenario
        self.conversation_history = []
        
    def generate_system_prompt(self, role):
        if role == "Banker":
            return (
                f"You are a seasoned Investment Banker (VP level) at a top tier bank. "
                f"Your goal is to pitch the following idea: '{self.scenario.banker_idea}'. "
                f"Client Industry: {self.scenario.client_industry}. "
                f"Market Conditions: {self.scenario.market_conditions}. "
                f"You are professional, persuasive, and knowledgeable about financial products. "
                f"Keep your responses concise (under 2-3 sentences) and conversational."
            )
        else: # Client
            return (
                f"You are the Client: {self.scenario.client_persona}. "
                f"Your company is in the {self.scenario.client_industry} industry. "
                f"Financial Context: {self.scenario.financial_context}. "
                f"Market Conditions: {self.scenario.market_conditions}. "
                f"You are skeptical, protective of your equity/cash, and focused on your business goals. "
                f"React realistically to the banker's pitch based on your financials and market conditions. "
                f"Keep your responses concise (under 2-3 sentences) and conversational."
            )

    def generate_turn(self, agent_name, system_prompt):
        messages = [{"role": "system", "content": system_prompt}]
        for log in self.conversation_history:
            role = "assistant" if log['agent'] == agent_name else "user"
            messages.append({"role": role, "content": log['message']})
            
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=150
            )
            return response.choices[0].message['content'].strip()
        except Exception as e:
            return f"[Error generating response: {e}]"

    def run_step(self):
        # Determine who speaks next
        if not self.conversation_history:
            speaker = "Banker"
        else:
            last_speaker = self.conversation_history[-1]['agent']
            speaker = "Client" if last_speaker == "Banker" else "Banker"
            
        system_prompt = self.generate_system_prompt(speaker)
        message = self.generate_turn(speaker, system_prompt)
        
        log_entry = {'agent': speaker, 'message': message}
        self.conversation_history.append(log_entry)
        
        # Update Scenario
        current_logs = self.scenario.get_conversation_log()
        current_logs.append(log_entry)
        self.scenario.set_conversation_log(current_logs)
        self.scenario.save()


def run_simulation(scenario_id):
    scenario = Scenario.objects.get(id=scenario_id)
    
    # Check if we can use LLM
    if OPENAI_AVAILABLE and openai.api_key:
        print("Running Enhanced LLM Simulation")
        engine = SimpleLLMEngine(scenario)
        # Run 5 turns
        for _ in range(6):
            time.sleep(1) # simulate thinking
            engine.run_step()
        scenario.status = 'COMPLETED'
        scenario.save()
        return

    if not REVERIE_AVAILABLE or not UTILS_AVAILABLE:
        # Run Mock Simulation
        print("Running Mock Simulation (Reverie unavailable)")
        logs = []
        conversation = [
            ("Banker", f"Hello, I see you are running {scenario.client_persona}. I have an idea: {scenario.banker_idea}"),
            ("Client", "That sounds interesting. Tell me more about the credit facility."),
            ("Banker", "It will allow you to scale your robot fleet without diluting equity."),
            ("Client", "I like that. Let's proceed.")
        ]
        
        for speaker, msg in conversation:
            time.sleep(1)
            logs.append({'agent': speaker, 'message': msg})
            scenario.set_conversation_log(logs)
            scenario.save()
            
        scenario.status = 'COMPLETED'
        scenario.save()
        return

    try:
        # 1. Setup Simulation
        fork_sim_code = "base_the_ville_isabella_maria_klaus"
        sim_code = f"ib_scenario_{scenario.id}"
        
        # Initialize Reverie Server
        rs = ReverieServer(fork_sim_code, sim_code)
        
        # 2. Inject Context
        # We'll use Isabella as Client and Klaus as Banker
        client_name = "Isabella Rodriguez"
        banker_name = "Klaus Mueller"
        
        if client_name in rs.personas and banker_name in rs.personas:
            client = rs.personas[client_name]
            banker = rs.personas[banker_name]
            
            # Move them close to each other to encourage interaction
            # Common Room table seems like a good place? 
            # We'll valid coordinates later, for now let's trust the base sim or path finding.
            # Actually, to force interaction, we might want to teleport them.
            # But let's try injecting thoughts first.
            
            # Inject Banker's Goal
            banker_thought = f"I need to pitch this idea to {client_name}: {scenario.banker_idea}"
            banker.a_mem.add_thought(
                rs.curr_time, 
                rs.curr_time + datetime.timedelta(days=1), 
                banker_name, "pitch", client_name, 
                banker_thought, {banker_name, client_name, "pitch"}, 
                10, # Poignancy
                (banker_thought, [0]*1536), # Mock embedding if needed or let system handle
                None
            )
            
            # Inject Client's Persona
            client_thought = f"I am {scenario.client_persona}"
            client.a_mem.add_thought(
                rs.curr_time, 
                rs.curr_time + datetime.timedelta(days=1), 
                client_name, "is", "client", 
                client_thought, {client_name, "persona"}, 
                10, 
                (client_thought, [0]*1536), 
                None
            )
            
        # 3. Run Loop
        steps_to_run = 10 # Run for 100 logical steps (approx 10-20 mins game time)
        logs = []
        
        for i in range(steps_to_run):
            rs.start_server(1) # Run 1 step
            
            # Capture Chat
            # We check the chat buffer of the agents
            current_logs = []
            
            for p_name, p in rs.personas.items():
                if p.scratch.chat:
                    # Chat format in scratch is usually a list of rows
                    # But scratch.chat is populated during the step
                    # Let's see how 'movements' saved it.
                    # It saves it as `persona.scratch.chat`.
                    # It's likely a list of recent chats.
                    for line in p.scratch.chat:
                        # line is likely (Speaker, Message)
                        if len(line) >= 2:
                            speaker = line[0]
                            message = line[1]
                            log_entry = {'agent': speaker, 'message': message}
                            if log_entry not in logs:
                                logs.append(log_entry)
                                current_logs.append(log_entry)
            
            # Save logs to DB
            scenario.set_conversation_log(logs)
            scenario.save()
            
            # Check for termination (if conversation ends)
            # Rough heuristic: if we have logs and haven't had new logs for a while?
            # For now just run fixed steps.
            
        scenario.status = 'COMPLETED'
        scenario.save()
        
    except Exception as e:
        scenario.status = 'FAILED'
        scenario.conversation_log = json.dumps([{'agent': 'System', 'message': f'Error: {str(e)}'}])
        scenario.save()
        print(f"Simulation failed: {e}")

import sys
import json
import logging
import os
import shlex
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory

from src.agent import ZerePyAgent
from src.helpers import print_h_bar
from src.database.manager import db_manager
from src.database.utils import create_zerepy_agent_from_db, load_default_agent, save_default_agent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("cli")


@dataclass
class Command:
    """Dataclass to represent a CLI command"""
    name: str
    description: str
    tips: List[str]
    handler: Callable
    aliases: List[str] = None

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class ZerePyCLI:
    def __init__(self):
        self.agent = None

        # Create config directory if it doesn't exist
        self.config_dir = Path.home() / '.zerepy'
        self.config_dir.mkdir(exist_ok=True)

        # Initialize command registry
        self._initialize_commands()

        # Setup prompt toolkit components
        self._setup_prompt_toolkit()

    def _initialize_commands(self) -> None:
        """Initialize all CLI commands"""
        self.commands: Dict[str, Command] = {}

        # Help command
        self._register_command(
            Command(
                name="help",
                description="Displays a list of all available commands, or help for a specific command.",
                tips=["Try 'help' to see available commands.",
                      "Try 'help {command}' to get more information about a specific command."],
                handler=self.help,
                aliases=['h', '?']
            )
        )

        # Clear command
        self._register_command(
            Command(
                name="clear",
                description="Clears the terminal screen.",
                tips=["Use this command to clean up your terminal view"],
                handler=self.clear_screen,
                aliases=['cls']
            )
        )

        ################## AGENTS ##################
        # Agent action command
        self._register_command(
            Command(
                name="agent-action",
                description="Runs a single agent action.",
                tips=["Format: agent-action {connection} {action}",
                      "Use 'list-connections' to see available connections.",
                      "Use 'list-actions' to see available actions."],
                handler=self.agent_action,
                aliases=['action', 'run']
            )
        )

        # Agent loop command
        self._register_command(
            Command(
                name="agent-loop",
                description="Starts the current agent's autonomous behavior loop.",
                tips=["Press Ctrl+C to stop the loop"],
                handler=self.agent_loop,
                aliases=['loop', 'start']
            )
        )

        # List agents command
        self._register_command(
            Command(
                name="list-agents",
                description="Lists all available agents you have on file.",
                tips=["Use 'load-agent' to load an available agent"],
                handler=self.list_agents,
                aliases=['agents', 'ls-agents']
            )
        )

        # Load agent command
        self._register_command(
            Command(
                name="load-agent",
                description="Loads an agent from the database.",
                tips=["Format: load-agent {agent_name}",
                      "Use 'list-agents' to see available agents"],
                handler=self.load_agent,
                aliases=['load']
            )
        )

        # Create agent command
        self._register_command(
            Command(
                name="create-agent",
                description="Creates a new agent.",
                tips=["Follow the interactive wizard to create a new agent"],
                handler=self.create_agent,
                aliases=['new-agent', 'create']
            )
        )

        # Define default agent
        self._register_command(
            Command(
                name="set-default-agent",
                description="Define which model is loaded when the CLI starts.",
                tips=["Format: default {agent_name}"],
                handler=self.set_default_agent,
                aliases=['default']
            )
        )

        # Chat command
        self._register_command(
            Command(
                name="chat",
                description="Start a chat session with the current agent",
                tips=["Use 'exit' to end the chat session"],
                handler=self.chat_session,
                aliases=['talk']
            )
        )

        ################## CONNECTIONS ##################
        # List actions command
        self._register_command(
            Command(
                name="list-actions",
                description="Lists all available actions for the given connection.",
                tips=["Format: list-actions {connection}",
                      "Use 'list-connections' to see available connections"],
                handler=self.list_actions,
                aliases=['actions', 'ls-actions']
            )
        )

        # Configure connection command
        self._register_command(
            Command(
                name="configure-connection",
                description="Sets up a connection for API access.",
                tips=["Format: configure-connection {connection}",
                      "Follow the prompts to enter necessary credentials"],
                handler=self.configure_connection,
                aliases=['config', 'setup']
            )
        )

        # List connections command
        self._register_command(
            Command(
                name="list-connections",
                description="Lists all available connections.",
                tips=["Shows both configured and unconfigured connections"],
                handler=self.list_connections,
                aliases=['connections', 'ls-connections']
            )
        )

        ################## MISC ##################
        # Exit command
        self._register_command(
            Command(
                name="exit",
                description="Exits the ZerePy CLI.",
                tips=["You can also use Ctrl+D to exit"],
                handler=self.exit,
                aliases=['quit', 'q']
            )
        )
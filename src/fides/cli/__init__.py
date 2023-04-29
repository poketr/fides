"""
Entrypoint for the Fides command-line.
"""
from importlib.metadata import version
from platform import system

from fideslog.sdk.python.client import AnalyticsClient
from rich_click import Context, echo, group, option, pass_context, secho, version_option

import fides
from fides.cli.utils import check_server
from fides.core.config import get_config

from . import cli_formatting
from .commands.annotate import annotate
from .commands.core import evaluate, parse, pull, push
from .commands.crud import delete, get_resource, list_resources
from .commands.db import database
from .commands.export import export
from .commands.generate import generate
from .commands.scan import scan
from .commands.user import user
from .commands.util import deploy, init, status, webserver, worker
from .commands.view import view
from .exceptions import LocalModeException

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
LOCAL_COMMANDS = [deploy, evaluate, generate, init, scan, parse, view, webserver]
LOCAL_COMMAND_NAMES = {command.name for command in LOCAL_COMMANDS}
API_COMMANDS = [
    annotate,
    database,
    delete,
    export,
    get_resource,
    list_resources,
    status,
    pull,
    push,
    worker,
    user,
]
ALL_COMMANDS = API_COMMANDS + LOCAL_COMMANDS
SERVER_CHECK_COMMAND_NAMES = {
    command.name for command in API_COMMANDS if command.name not in ["status", "worker"]
}
VERSION = fides.__version__
APP = fides.__name__
PACKAGE = "ethyca-fides"


@group(
    context_settings=CONTEXT_SETTINGS,
    invoke_without_command=True,
    name="fides",
)
@version_option(version=VERSION)
@option(
    "--config-path",
    "-f",
    "config_path",
    show_default=True,
    help="Path to a Fides config file. _Defaults to `.fides/fides.toml`._",
)
@option(
    "--local",
    is_flag=True,
    help="Run in `local_mode`. Where possible, this will force commands to run without the need for a server.",
)
@pass_context
def cli(ctx: Context, config_path: str, local: bool) -> None:
    """
    __Command-line tool for the Fides privacy engineering platform.__

    ---

    _Note: The common MANIFESTS_DIR argument _always_ defaults to ".fides/" if not specified._
    """

    ctx.ensure_object(dict)
    config = get_config(config_path, verbose=True)
    command = ctx.invoked_subcommand or ""

    if not (local or config.cli.local_mode):
        config.cli.local_mode = False
    else:
        config.cli.local_mode = True

    if config.cli.local_mode and command not in LOCAL_COMMAND_NAMES:
        raise LocalModeException(command)

    # Run the help command if no subcommand is passed
    if not command:
        echo(cli.get_help(ctx))

    # Check the server health and version if an API command is invoked
    if command in SERVER_CHECK_COMMAND_NAMES:
        check_server(VERSION, str(config.cli.server_url), quiet=True)

    # Analytics requires explicit opt-in
    no_analytics = config.user.analytics_opt_out
    if not no_analytics:
        ctx.meta["ANALYTICS_CLIENT"] = AnalyticsClient(
            client_id=config.cli.analytics_id,
            developer_mode=config.test_mode,
            os=system(),
            product_name=APP + "-cli",
            production_version=version(PACKAGE),
        )

    # Setting the config context after all mutations
    ctx.obj["CONFIG"] = config


# Add all commands here before dynamically checking them in the CLI
for cli_command in ALL_COMMANDS:
    cli.add_command(cli_command)

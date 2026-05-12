import typer
import json

from logique import init_config, set_config, get_config


def register_commands(app: typer.Typer):

    # =========================================================
    # CONFIG COMMAND GROUP
    # =========================================================

    @app.command()
    def config(
        action: str = typer.Argument(None),  # init / set / get
        storage: str = typer.Option(None, "--storage"),
        password: str = typer.Option(None, "--password"),
        ram_limit: int = typer.Option(None, "--ram-limit"),
        disk_limit: int = typer.Option(None, "--disk-limit"),
        json_mode: bool = typer.Option(False, "--json")
    ):
        """
        config init | config set | config get
        """

        # =========================================================
        # INIT
        # =========================================================
        if action == "init":
            result = init_config(storage, password, ram_limit, disk_limit)

        # =========================================================
        # SET
        # =========================================================
        elif action == "set":
            result = set_config(storage, password, ram_limit, disk_limit)

        # =========================================================
        # GET
        # =========================================================
        else:
            result = get_config()

        # =========================================================
        # OUTPUT
        # =========================================================
        if json_mode:
            print(json.dumps(result, indent=2))
        else:
            print("CONFIG:")
            print(json.dumps(result, indent=2))
import typer
import pathlib
import logging
import yaml
from enum import Enum
from conda_store.app import CondaStore
from conda_store.build import start_conda_build
from conda_store import client
from conda_store.server import start_app

logger = logging.getLogger(__name__)

def initialize_cli():
    app = typer.Typer()

    build_app = typer.Typer()
    server_app = typer.Typer()
    env_app = typer.Typer()
    pkgs_app = typer.Typer()

    app.add_typer(build_app, name="build")
    app.add_typer(env_app, name="env")
    env_app.add_typer(pkgs_app, name="package")
    app.add_typer(server_app, name="serve")

    StorageBackends = Enum('StorageBackends', dict(fs='filesystem', s3='s3'))

    @build_app.callback()
    def _handle_conda_store_build(
            environment: str = typer.Option(..., "--environment", "-e"),
            store: str = typer.Option(".conda-store", "--store", "-s"),
            paths: pathlib.Path = typer.Option("", "--paths", "-p", show_default=False),
            uid: int = typer.Option(None, "--uid"),
            gid: int = typer.Option(None, "--gid"),
            permissions: str = typer.Option("",  help="permissions to assign to built environments"),
            storage_threshold: int = typer.Option((5 * (2**30)), "--storage-threshold", help="emit warning when free disk space drops below threshold bytes"),
            storage_backend: str = typer.Option(StorageBackends.s3),
            poll_interval: int = typer.Option(10, "--poll-interval", help="poll interval to check environment directory for new environments"),
            ):

        conda_store = CondaStore(
            store_directory=store,
            database_url=None,
            storage_backend=storage_backend)

        environment_directory = pathlib.Path(
            environment or
            conda_store.configuration.environment_directory or
            (conda_store.configuration.store_directory / 'envs')).resolve()
        if not environment_directory.is_dir():
            logger.info(f'creating directory environment_directory={environment_directory}')
            environment_directory.mkdir(parents=True)
        conda_store.configuration.environment_directory = str(environment_directory)

        if permissions:
            conda_store.configuration.default_permissions = permissions
        if uid:
            conda_store.configuration.default_uid = uid
        if gid:
            conda_store.configuration.default_gid = gid

        conda_store.update_storage_metrics()
        conda_store.update_conda_channels()

        start_conda_build(conda_store, paths, storage_threshold, poll_interval)

    @env_app.command("create")
    def _env_create_from_file(
            filename: typer.FileText = typer.Option(..., "--filename", "-f", help="A conda file supplied with the environment details"),
            ):
        with open(filename) as f:
            data = yaml.safe_load(f)
        client.post_specification(data)

    @env_app.command("list")
    def _env_list():
        data = client.get_environments()
        print('{:10}{:32}{:32}'.format('BUILD', 'NAME', 'SHA256'))
        print("="*74)
        for row in data:
            name = row['name']
            build_id = row['build_id']
            sha256 = row.get('specification', {}).get('sha256')
            print(f'{build_id:<10}{name:32}{sha256[:32]:32}')

    @pkgs_app.command("list")
    def _env_list_packages(
            name: str = typer.Option(..., "--name", "-n", help="A conda store environment name")
            ):
        data = client.get_environment_packages(name=name)
        print('{:32}{:16}{:48}{:32}'.format('NAME', 'VERSION', 'LICENSE', 'SHA256'))
        print("="*128)
        pkgs = data['specification']['builds'][0]['packages']
        for pkg in pkgs:
            name = pkg['name']
            version = pkg['version']
            license = pkg['license']
            sha = pkg['sha256']
            print(f'{name:32}{version:16}{license:48}{sha:32}')

    @server_app.callback()
    def _handle_conda_store_server(
        address: str = typer.Option("0.0.0.0", "--address"),        port: int = typer.Option(5000, help="port to run conda-store ui"),
        store: str = typer.Option(".conda-store", "--store","-s"),
        storage_backend: str = typer.Option(StorageBackends.s3),
        disable_ui: bool = typer.Option(False, "--disable-ui"),
        disable_api: bool = typer.Option(False, "--disable-api"),
        disable_registry: bool = typer.Option(False, "--disable-registry"),
        verbose: bool = typer.Option(False, "--verbose")
    ):
        start_app(
            store, storage_backend,
            disable_ui=disable_ui,
            disable_api=disable_api,
            disable_registry=disable_registry,
            address=address,
            port=port)

    app()

import click


@click.group()
def main():
    """Kollektiv CLI tool"""
    pass


@main.command()
def api():
    """Run the Kollektiv api server"""
    from src.app import run

    run()


@main.command()
def worker():
    """Run the Kollektiv worker"""
    from src.infra.arq.worker import run_worker

    run_worker()

import argparse
import sys


def parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="visagecam", description="VisageCam")
    parser.add_argument("--install-shortcuts", action="store_true", help="crea el acceso directo en el menu Inicio")
    parser.add_argument("--desktop", action="store_true", help="con --install-shortcuts, crea tambien uno en el escritorio")
    parser.add_argument("--remove-shortcuts", action="store_true", help="elimina los accesos directos")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse(sys.argv[1:] if argv is None else argv)
    if args.install_shortcuts or args.remove_shortcuts:
        from visagecam import shortcuts

        if args.remove_shortcuts:
            for path in shortcuts.remove():
                print(f"Eliminado: {path}")
        if args.install_shortcuts:
            for path in shortcuts.install(desktop=args.desktop):
                print(f"Creado: {path}")
        return 0
    from visagecam.app import main as run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())

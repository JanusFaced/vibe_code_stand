from loops import (
    simple,
    no_history,
)

def run_vibecoding() -> None:
    variant = 'no_history'

    if variant == 'simple':
        simple.main()
    elif variant == 'no_history':
        no_history.main()

if __name__ == "__main__":
    run_vibecoding()



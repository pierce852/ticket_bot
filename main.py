import sys
from cityline_bot import run as cityline_run
from urbtix_bot import run as urbtix_run

def main():
    print("Welcome to the Cityline/UrbTix Ticket Bot!")
    print("Select a platform:")
    print("1. Cityline")
    print("2. UrbTix")
    choice = input("Enter platform number (1/2): ").strip()
    if choice == '1':
        cityline_run()
    elif choice == '2':
        urbtix_run()
    else:
        print("Invalid choice. Please restart and select 1 or 2.")
        sys.exit(1)

if __name__ == "__main__":
    main() 
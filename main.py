import sys
from cityline_bot import run as cityline_run
from urbtix_bot import run as urbtix_run

def main():
    print("歡迎使用 Cityline/UrbTix 搶票機器人！")
    print("請選擇平台：")
    print("1. Cityline")
    print("2. UrbTix")
    choice = input("請輸入數字選擇平台 (1/2)：").strip()
    if choice == '1':
        cityline_run()
    elif choice == '2':
        urbtix_run()
    else:
        print("輸入錯誤，請重新啟動程式並選擇 1 或 2。")
        sys.exit(1)

if __name__ == "__main__":
    main() 
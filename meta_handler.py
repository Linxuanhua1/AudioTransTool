from lib.lib_meta_handler import Action
import os


os.environ['PATH'] = os.environ['PATH'] + os.pathsep + os.getcwd() + '/bin/'


if __name__ == '__main__':
    while True:
        print('-' * 50)
        print("请选择操作：")
        for idx, action in enumerate(Action, 1):
            print(f"{idx}. {action.display_name}")
        print("0. 退出")
        try:
            choice = int(input("输入数字: "))
            if choice == 0:
                print("已退出程序。")
                break
            print('-' * 50)
            selected_action = list(Action)[choice - 1]
            selected_action.func()
        except (ValueError, IndexError):
            print("无效的选择")
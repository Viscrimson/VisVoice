from managers.Queue_manager import QueueManager
from managers.UI_manager import UIManager

def main():
    queue_manager = QueueManager()
    ui_manager = UIManager(queue_manager)
    ui_manager.run()

if __name__ == '__main__':
    main()

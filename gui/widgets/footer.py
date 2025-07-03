from textual.widgets import Footer


class MyFooter(Footer):
    def get_shortcuts(self):
        return [
            ("F1", "帮助", "help"),
            ("Q", "退出", "quit"),
            ("Tab", "切换面板", "tab"),
            ("←/→", "切换合约", "switch-symbol"),
            ("R", "刷新", "refresh"),
            ("Space", "暂停/继续", "pause/resume"),
            # 你还可以添加更多自定义快捷键
        ]

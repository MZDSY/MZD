# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import time
import os

from uiautomation import WindowControl

# ============ 剪贴板相关 ============
try:
    import win32clipboard
    import win32con

    USE_CLIPBOARD = True
except ImportError:
    print("提示: 安装 pywin32 可获得更好的中文支持")
    print("运行: pip install pywin32")
    USE_CLIPBOARD = False


def set_clipboard(text):
    """设置剪贴板内容"""
    if USE_CLIPBOARD:
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
            win32clipboard.CloseClipboard()
            return True
        except:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass
    return False


def send_message(window, text):
    """发送消息"""
    if USE_CLIPBOARD and set_clipboard(text):
        window.SendKeys('{Ctrl}v', waitTime=0.2)
        time.sleep(0.2)
        window.SendKeys('{Enter}', waitTime=0.2)
    else:
        window.SendKeys(text.replace('{br}', '{Shift}{Enter}'), waitTime=0)
        window.SendKeys('{Enter}', waitTime=0)


def click_first_chat(wx):
    """点击第一个置顶的会话"""
    try:
        hw = wx.ListControl(Name='会话')
        if hw.Exists(0.5, 0.5):
            children = hw.GetChildren()
            if children:
                children[0].Click(simulateMove=False)
                return True
    except:
        pass
    return False


def close_other_windows(main_wx):
    """关闭除主窗口外的其他微信聊天窗口"""
    try:
        # 查找所有可能的独立聊天窗口并关闭
        import uiautomation as auto
        for win in auto.GetRootControl().GetChildren():
            if win.ClassName and 'ChatWnd' in win.ClassName:
                try:
                    win.SendKeys('{Alt}{F4}', waitTime=0.1)
                except:
                    pass
    except:
        pass


# ============ 初始化 ============

print("=" * 50)
print("   微信自动回复程序")
print("=" * 50)

# 查找微信
wx = WindowControl(Name='微信')
if not wx.Exists(3, 3):
    print('错误: 未找到微信窗口，请确保微信已打开')
    input("按回车退出...")
    exit()

print('✓ 找到微信窗口')
wx.SwitchToThisWindow()

# 获取会话列表控件
hw = wx.ListControl(Name='会话')
if not hw.Exists(3, 3):
    print('错误: 未找到会话列表')
    input("按回车退出...")
    exit()

print('✓ 找到会话列表')

# 获取第一个置顶会话名称
first_chat_name = ""
children = hw.GetChildren()
if children:
    first_chat_name = children[0].Name
    print(f'✓ 第一个置顶会话: {first_chat_name}')

# 读取自动回复内容
csv_file = '自动回复内容.csv'
if os.path.exists(csv_file):
    df = pd.read_csv(csv_file, encoding='utf-8')
    print(f'✓ 加载了 {len(df)} 条回复规则')
else:
    df = pd.DataFrame({
        '关键词': ['你好', '在吗', '在不在', '谢谢', '?', '？'],
        '回复内容': ['你好呀~', '在的，有事吗？', '在呢', '不客气', '稍后回复你', '稍后回复你']
    })
    df.to_csv(csv_file, index=False, encoding='utf-8')
    print(f'✓ 已创建示例配置文件: {csv_file}')

DEFAULT_REPLY = '我现在有事不在，稍后回复你（自动回复）'

# 已处理消息记录
processed_messages = {}

print("\n" + "-" * 50)
print("开始监听所有好友消息，按 Ctrl+C 停止")
print("-" * 50 + "\n")

# 先点击第一个会话，确保初始状态正确
click_first_chat(wx)
time.sleep(0.5)

# ============ 主循环 ============

while True:
    try:
        # 重新获取微信窗口
        wx = WindowControl(Name='微信')
        if not wx.Exists(0, 0):
            print(f'[{time.strftime("%H:%M:%S")}] 微信窗口未找到，等待中...')
            time.sleep(3)
            continue

        try:
            wx.SwitchToThisWindow()
        except:
            pass

        # 关闭可能存在的独立窗口
        close_other_windows(wx)

        # 获取会话列表
        hw = wx.ListControl(Name='会话')
        if not hw.Exists(0, 0):
            print(f'[{time.strftime("%H:%M:%S")}] 会话列表未找到')
            time.sleep(2)
            continue

        # 遍历会话列表查找未读消息（从第二个开始，跳过第一个置顶）
        children = hw.GetChildren()
        found_unread = False

        for i, child in enumerate(children):
            # 检查是否有未读消息标记
            unread_badge = child.TextControl(searchDepth=2)
            if not unread_badge.Exists(0, 0):
                continue

            badge_name = unread_badge.Name
            if not badge_name or not (badge_name.isdigit() or '条' in badge_name):
                continue

            # 找到未读消息
            chat_name = child.Name
            display_name = chat_name.replace('已置顶', '').strip() if chat_name else '未知'

            found_unread = True
            print(f'[{time.strftime("%H:%M:%S")}] 📩 {display_name} ({badge_name}条未读)')

            # 点击进入会话
            child.Click(simulateMove=False)
            time.sleep(1)

            # 获取消息列表（在主窗口中查找）
            msg_list = wx.ListControl(Name='消息')
            if not msg_list.Exists(1, 1):
                print('    消息列表未找到')
                click_first_chat(wx)
                time.sleep(0.5)
                continue

            msg_controls = msg_list.GetChildren()
            if not msg_controls:
                print('    没有消息')
                click_first_chat(wx)
                time.sleep(0.5)
                continue

            # 获取最后一条有效消息
            last_msg = None
            for msg in reversed(msg_controls):
                msg_text = msg.Name
                if msg_text and msg_text.strip():
                    if msg_text.startswith('[') and msg_text.endswith(']'):
                        continue
                    if '撤回了一条消息' in msg_text:
                        continue
                    last_msg = msg_text.strip()
                    break

            if not last_msg and msg_controls:
                last_msg = msg_controls[-1].Name

            if not last_msg:
                print('    无法获取消息内容')
                click_first_chat(wx)
                time.sleep(0.5)
                continue

            show_msg = last_msg[:35] + '...' if len(last_msg) > 35 else last_msg
            print(f'    收到: {show_msg}')

            # 检查是否已处理过
            if chat_name in processed_messages and processed_messages[chat_name] == last_msg:
                print('    [跳过] 已回复过')
                click_first_chat(wx)
                time.sleep(0.5)
                continue

            # 匹配自动回复内容
            reply = None
            matched_keyword = None

            for _, row in df.iterrows():
                keyword = str(row['关键词'])
                if keyword in last_msg:
                    reply = str(row['回复内容'])
                    matched_keyword = keyword
                    break

            if matched_keyword:
                print(f'    匹配关键词: [{matched_keyword}]')
            else:
                reply = DEFAULT_REPLY
                print('    使用默认回复')

            # 发送回复
            time.sleep(0.3)
            send_message(wx, reply)
            print(f'    ✓ 已回复: {reply[:30]}...' if len(reply) > 30 else f'    ✓ 已回复: {reply}')

            # 记录已处理
            processed_messages[chat_name] = last_msg

            # 清理缓存
            if len(processed_messages) > 200:
                keys = list(processed_messages.keys())
                for key in keys[:100]:
                    del processed_messages[key]

            # ============ 关键：点击回到第一个置顶窗口 ============
            time.sleep(0.5)
            click_first_chat(wx)
            print(f'    [已返回第一个置顶窗口]')

            time.sleep(1)
            break

        # 等待
        if not found_unread:
            time.sleep(2)
        else:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n程序已停止")
        break
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 错误: {str(e)}")
        # 出错时也尝试返回第一个窗口
        try:
            click_first_chat(wx)
        except:
            pass
        time.sleep(3)
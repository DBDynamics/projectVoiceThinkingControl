from rich import print
from rich.prompt import Prompt

from brain import Memory
from tts import speak
from stt import STT


def main() -> None:
    mem = Memory()

    print("[bold cyan]projectVoiceThinkingControl[/bold cyan]")
    print("[green]示例：[/green] 苹果在120度 鸭梨在240度 西瓜在360度")
    print("[green]查询：[/green] 我说 西瓜  或  直接输入 西瓜")
    print("[green]退出：[/green] 退出 / exit / quit")
    print("[green]语音模式：[/green] 输入 语音模式 / voice 进入麦克风识别")

    while True:
        try:
            line = Prompt.ask("[bold]>>>[/bold]").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[yellow]已退出[/yellow]")
            break

        if not line:
            continue

        if line.lower() in {"exit", "quit"} or line == "退出":
            print("[yellow]已退出[/yellow]")
            break

        # 进入语音模式
        if line in {"语音模式", "voice"}:
            if not STT().available():
                print("[red]未检测到Vosk中文模型，请先下载到 models/vosk-model-small-cn-0.22[/red]")
                print("[yellow]查看README中的‘语音说明’与‘模型下载’部分[/yellow]")
                continue
            print("[cyan]语音模式已启动：说‘退出’停止[/cyan]")
            # 构建受限词表以提升识别准确度（包含常见水果、已记录项、数字与控制词）
            base_items = ["苹果", "鸭梨", "西瓜", "葡萄", "香蕉", "橙子", "柠檬", "草莓"]
            known_items = list(mem.store.keys())
            
            # 扩展数字词汇，包含常见组合
            digits_words = [
                # 基础数字
                "零", "〇", "O", "o", "一", "二", "两", "三", "四", "五", "六", "七", "八", "九", "十", "百", "千",
                # 常见数字组合
                "一十", "二十", "三十", "四十", "五十", "六十", "七十", "八十", "九十",
                "一百", "二百", "三百", "四百", "五百", "六百", "七百", "八百", "九百",
                "一百八", "二百四", "三百六", "一百二", "二百八", "三百二",
                "一百八十", "二百四十", "三百六十", "一百二十", "二百八十", "三百二十",
                # 度数相关
                "度", "读", "毒", "独",
                # 常见误识别词
                "把", "本", "而", "尔", "儿", "是", "实", "石", "拾", "意",
            ]
            
            # 扩展控制词和常用表达
            control_words = [
                "我说", "握手", "我收", "在", "是", "度", "退出", "结束", "停止",
                "苹果在", "西瓜在", "鸭梨在", "葡萄在",
                "一百八十度", "二百四十度", "三百六十度", "一百二十度",
                "我说苹果", "我说西瓜", "我说鸭梨", "我说葡萄"
            ]
            
            grammar_words = list(set(base_items + known_items + digits_words + control_words))
            stt = STT(grammar_words=grammar_words)
            try:
                for text in stt.listen():
                    if not text:
                        continue
                    print(f"[magenta]识别：[/magenta]{text}")
                    if text in {"退出", "结束", "停止"}:
                        speak("已退出语音模式")
                        print("[yellow]已退出语音模式[/yellow]")
                        break
                    
                    # 先尝试作为知识录入
                    taught = mem.teach(text)
                    if taught:
                        speak("已记录")
                        print("[cyan]已记录[/cyan]")
                        # 录入后，动态扩展词表（若新物体出现）
                        if any(i not in grammar_words for i, _ in taught):
                            grammar_words = list(set(grammar_words + [i for i, _ in taught]))
                        continue
                    
                    # 否则作为查询
                    item = mem.maybe_extract_item_from_phrase(text) or text
                    deg = mem.query(item)
                    if deg is not None:
                        print(f"[bold green]{item}[/bold green]: [bold]{deg}度[/bold]")
                        speak("找到了")
                    else:
                        # 如果没有找到，尝试使用大模型进行智能纠错和重新解析
                        try:
                            from llm import interpret_text
                            print(f"[yellow]尝试智能解析：{text}[/yellow]")
                            result = interpret_text(text)
                            
                            # 如果大模型解析出了教学内容
                            if result.get("pairs"):
                                for item_name, degree in result["pairs"]:
                                    mem.store[item_name] = degree
                                    print(f"[cyan]智能解析并记录：{item_name} -> {degree}度[/cyan]")
                                speak("智能解析成功，已记录")
                                # 更新词表
                                new_items = [item for item, _ in result["pairs"]]
                                grammar_words = list(set(grammar_words + new_items))
                            # 如果大模型解析出了查询内容
                            elif result.get("query_item"):
                                query_item = result["query_item"]
                                deg = mem.query(query_item)
                                if deg is not None:
                                    print(f"[bold green]智能解析查询 {query_item}[/bold green]: [bold]{deg}度[/bold]")
                                    speak("智能解析成功，找到了")
                                else:
                                    print(f"[bold red]智能解析查询 {query_item}，但没有找到[/bold red]")
                                    speak("智能解析成功，但没有找到")
                            else:
                                print("[bold red]没有找到[/bold red]")
                                speak("没有找到")
                        except Exception as llm_error:
                            print(f"[yellow]智能解析失败：{llm_error}[/yellow]")
                            print("[bold red]没有找到[/bold red]")
                            speak("没有找到")
            except Exception as e:
                print(f"[red]语音模式异常：{e}[/red]")
            continue

        # 尝试作为知识录入
        taught = mem.teach(line)
        if taught:
            summary = ", ".join([f"{i}:{mem.normalize_degree(d)}度" for i, d in taught])
            print(f"[cyan]已记录：[/cyan]{summary}")
            speak("已记录")
            continue

        # 尝试作为查询（支持“我说 西瓜”）
        item = mem.maybe_extract_item_from_phrase(line) or mem.extract_item_llm(line) or line
        deg = mem.query(item)
        if deg is not None:
            print(f"[bold green]{item}[/bold green]: [bold]{deg}度[/bold]")
            speak("找到了")
        else:
            print("[bold red]没有找到[/bold red]")
            speak("没有找到")


if __name__ == "__main__":
    main()
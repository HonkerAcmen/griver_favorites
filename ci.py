#!/usr/bin/env python3
"""轻量级本地 CI：格式化 → 测试 → 提交 → 推送。"""

import argparse
import importlib.util
import subprocess
import sys

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

BLACK_TARGETS = ["apps", "tests", "ci.py"]
TOTAL_STEPS = 4


def log_info(msg: str) -> None:
    print(f"{BLUE}[INFO]{RESET} {msg}")


def log_success(msg: str) -> None:
    print(f"{GREEN}[SUCCESS]{RESET} {msg}")


def log_warn(msg: str) -> None:
    print(f"{YELLOW}[WARN]{RESET} {msg}")


def log_error(msg: str) -> None:
    print(f"{RED}[ERROR]{RESET} {msg}")


def run_cmd(
    cmd: list[str] | str,
    *,
    shell: bool = False,
    capture_output: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            cmd,
            shell=shell,
            check=check,
            capture_output=capture_output,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        display = cmd if isinstance(cmd, str) else " ".join(cmd)
        log_error(f"执行命令失败: '{display}'")
        if e.stderr:
            print(f"{RED}错误信息:\n{e.stderr.strip()}{RESET}")
        raise


def check_git_repo() -> None:
    res = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        log_error("当前目录不是一个有效 Git 仓库！")
        sys.exit(1)


def get_current_branch() -> str:
    res = run_cmd(["git", "branch", "--show-current"], capture_output=True)
    return res.stdout.strip()


def has_changes() -> bool:
    res = run_cmd(["git", "status", "--porcelain"], capture_output=True)
    return bool(res.stdout.strip())


def resolve_commit_message(message: str | None) -> str | None:
    if message and message.strip():
        return message.strip()

    log_warn("提交流水线需要 commit 信息。请通过 -m 传入，或在下方输入。")
    log_info("直接回车将取消，不会执行格式化与测试。")
    commit_msg = input(f"{BOLD}{YELLOW}📝 Commit 信息: {RESET}").strip()
    if not commit_msg:
        log_warn("未提供 commit 信息，流水线已取消。")
        return None
    return commit_msg


def run_module(module: str, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", module, *extra], shell=False)


def run_black() -> None:
    log_info(f"步骤 1/{TOTAL_STEPS}: black 格式化 ({' '.join(BLACK_TARGETS)})...")

    if importlib.util.find_spec("black") is None:
        log_warn("当前 Python 环境未安装 black，跳过（pip install black）")
        return

    run_module("black", *BLACK_TARGETS)
    log_success("代码格式化完成。")


def run_pytest() -> bool:
    log_info(f"步骤 2/{TOTAL_STEPS}: 运行 pytest...")

    if importlib.util.find_spec("pytest") is None:
        log_warn("当前 Python 环境未安装 pytest，跳过。")
        return True

    res = run_module("pytest")
    if res.returncode != 0:
        log_error("测试未通过，已终止提交与推送。")
        return False

    log_success("所有测试通过。")
    return True


def git_commit(commit_msg: str) -> None:
    log_info(f"步骤 3/{TOTAL_STEPS}: 暂存并提交...")
    run_cmd(["git", "add", "."])
    run_cmd(["git", "commit", "-m", commit_msg])
    log_success(f"本地提交成功: {commit_msg!r}")


def git_push(branch: str) -> None:
    log_info(f"步骤 4/{TOTAL_STEPS}: 推送到 origin/{branch}...")
    run_cmd(["git", "push", "origin", branch])
    log_success(f"已推送到 GitHub ({branch})。")


def cmd_test_only() -> None:
    print(f"\n{BOLD}{BLUE}======== 仅运行测试 ========{RESET}\n")
    if not run_pytest():
        sys.exit(1)
    print(f"\n{BOLD}{GREEN}======== 测试完成 ========{RESET}\n")


def cmd_release(message: str | None, *, skip_test: bool, no_push: bool) -> None:
    print(
        f"\n{BOLD}{BLUE}================ 🚀 本地 CI 流水线 ================ {RESET}\n"
    )

    check_git_repo()
    branch = get_current_branch()
    log_info(f"当前分支: {BOLD}{GREEN}{branch}{RESET}")

    commit_msg = resolve_commit_message(message)
    if commit_msg is None:
        sys.exit(0)

    dirty = has_changes()

    if not dirty:
        log_warn("工作区无改动；仍将执行检查，但不会 commit / push。")

    run_black()

    if not skip_test and not run_pytest():
        sys.exit(1)

    if not has_changes():
        log_warn("没有可提交的文件，流水线结束。")
        sys.exit(0)

    try:
        git_commit(commit_msg)
    except subprocess.CalledProcessError:
        log_error("git commit 失败。")
        sys.exit(1)

    if no_push:
        log_info("已跳过 push（--no-push）。")
    else:
        try:
            git_push(branch)
        except subprocess.CalledProcessError:
            log_error("git push 失败，请检查网络或远程权限。")
            sys.exit(1)

    print(
        f"\n{BOLD}{GREEN}================ ✨ CI 流水线完成 ================ {RESET}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="本地 CI：格式化、测试、提交、推送。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python ci.py -m "feat: add item remove"     完整流水线（推荐）
  python ci.py test                             只跑 pytest
  python ci.py -m "fix: x" --no-push            提交但不推送
  python ci.py                                  查看帮助，不执行任何操作
        """.strip(),
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["test"],
        help="子命令：test = 仅运行 pytest",
    )
    parser.add_argument("-m", "--message", help="commit 说明")
    parser.add_argument("--skip-test", action="store_true", help="跳过 pytest")
    parser.add_argument("--no-push", action="store_true", help="提交但不 push")

    args = parser.parse_args()

    if args.command == "test":
        cmd_test_only()
        return

    if args.message is None:
        parser.print_help()
        print()
        log_warn("未提供 -m 且未使用 test 子命令，未执行任何操作。")
        log_info('提交并推送: python ci.py -m "你的 commit 信息"')
        log_info("仅跑测试:   python ci.py test")
        sys.exit(0)

    cmd_release(args.message, skip_test=args.skip_test, no_push=args.no_push)


if __name__ == "__main__":
    main()

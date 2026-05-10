"""python -m peilian.server 入口。"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="PeiLian 陪练系统 Web 服务")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址（默认 127.0.0.1）")
    parser.add_argument("--port", type=int, default=8000, help="监听端口（默认 8000）")
    parser.add_argument("--reload", action="store_true", help="启用热重载（开发场景）")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(
        "peilian.server.app:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        factory=True,
    )


if __name__ == "__main__":
    main()

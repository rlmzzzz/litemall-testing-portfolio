"""
公共配置（pytest 会自动加载）。
关键：让本机请求不走系统代理，否则会像你 litemall 项目里那样返回 502。
"""
import os

os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

#!/usr/bin/env python3
# coding: utf-8

import json
import sys

import requests

import voice

TULING_APIKEY = ""
GOODBYE = "再见。"
USERID = "pyconsole123"
WELCOME = "你好，欢迎使用图灵机器人。"


def get_ip_location():
    url = "http://ip.chinaz.com/getip.aspx"
    r = requests.get(url)
    ipstr = r.text
    ipdict = eval(ipstr, type('Dummy', (dict,), dict(__getitem__=lambda s, n: n))())
    return ipdict["address"].split()[0]


def query_loop():
    results = voice.baidu_voice_rec()
    if results is False:
        print(GOODBYE)
        voice.get_baidu_voice(GOODBYE)
        sys.exit(0)
    if not isinstance(results, list):
        print(results)
        return
    result = results[0]
    print("Result: %s" % result)
    location = get_ip_location()
    payload = {"key": TULING_APIKEY, "info": result, "userid": USERID, "loc": location}
    ret = requests.post("http://www.tuling123.com/openapi/api", data=payload)
    result = json.loads(ret.text)
    code = result["code"]
    if code == 100000:
        print(result["text"])
        voice.get_baidu_voice(result["text"])
    elif code == 200000:
        print(result["text"], result["url"])
        voice.get_baidu_voice(result["text"])
    elif code == 302000:
        print(result["text"])
        voice.get_baidu_voice(result["text"])
        for item in result["list"]:
            print("%s - %s" % (item["article"], item["source"]))
            voice.get_baidu_voice(result["article"])
            print("%s" % item["detailurl"])
    elif code == 308000:
        print(result["text"])
        voice.get_baidu_voice(result["text"])
        for item in result["list"]:
            print("%s" % item["name"])
            voice.get_baidu_voice(item["name"])
            print("%s" % item["detailurl"])


if __name__ == "__main__":
    print(WELCOME)
    voice.get_baidu_voice(WELCOME)
    while (True):
        query_loop()

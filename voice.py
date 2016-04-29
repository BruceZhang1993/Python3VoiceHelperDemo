#!/usr/bin/env python3
# coding: utf-8

import json
import os
import signal
import subprocess
import sys
import uuid
import wave

import pyaudio
import requests

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 8000
# RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "output.wav"

# 在此输入百度语音API Key和Secret Key
apikey = ""
secret = ""

p = None
stream = None
frames = []


def _retrieve_token(api_key, secret_key):
    '''
    向百度服务器获取token，返回token
    参数：
        api_key - API Key
        secret_key - Secret Key
    '''
    data = {"grant_type": "client_credentials", "client_id": api_key, "client_secret": secret_key}
    r = requests.post("https://openapi.baidu.com/oauth/2.0/token", data)
    j = json.loads(r.text)
    token = j["access_token"]
    tokenfile = open(os.getcwd() + "/token.save", "w")
    tokenfile.write(token)
    tokenfile.close()
    return token


def get_token():
    '''
    百度应用token获取，检查历史token记录
    无参数
    '''
    if os.path.exists("token.save"):
        tokenfile = open(os.getcwd() + "/token.save", "r")
        token = tokenfile.read()
        tokenfile.close()
        return token
    else:
        return _retrieve_token(apikey, secret)


def get_mac_address():
    '''
    获取本机MAC地址作为唯一识别码
    '''
    mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
    return ":".join([mac[e:e + 2] for e in range(0, 11, 2)])


def get_baidu_voice(text, lang="zh", speed=5, pitch=5, volumn=5, person=0):
    '''
    百度语音合成，成功保存和播放二进制mp3文件，失败打印错误码
    参数：
        text - 要合成文本
        lang - 语言，默认中文
        speed - 语速，取值0-9，默认5
        pitch - 语调，同上
        volumn - 音量，同上
        person - 取值0或1，0为女性，1为男性，默认女性
    '''
    token = get_token()
    mac = get_mac_address()
    r = requests.get(
        "http://tsn.baidu.com/text2audio?tex=%s&lan=%s&cuid=%s&ctp=1&tok=%s&spd=%d&pit=%d&vol=%d&per=%d" % (
            text, lang, mac, token, speed, pitch, volumn, person))
    if r.headers.get("content-type") == "audio/mp3":
        print("Success.")
        fw = open(os.getcwd() + "/tts.mp3", "wb")
        fw.write(r.content)
        fw.close()
        subprocess.Popen(['mpg123', '-q', os.getcwd() + "/tts.mp3"]).wait()
        print("Playback Finished.")
    elif r.headers.get("content-type") == "application/json":
        content = json.loads(r.text)
        print("Failed. Error: %d, %s." % (content["err_no"], content["err_msg"]))
        if content["err_no"] == 502:
            print("Trying to request token...")
            try:
                os.unlink(os.getcwd() + "/token.save")
            finally:
                token = get_token()
                r = requests.get(
                    "http://tsn.baidu.com/text2audio?tex=%s&lan=%s&cuid=%s&ctp=1&tok=%s&spd=%d&pit=%d&vol=%d&per=%d" % (
                        text, lang, mac, token, speed, pitch, volumn, person))
                if r.headers.get("content-type") == "audio/mp3":
                    print("Success.")
                    fw = open(os.getcwd() + "/tts.mp3", "wb")
                    fw.write(r.content)
                    fw.close()
                    subprocess.Popen(['mpg123', '-q', os.getcwd() + "/tts.mp3"]).wait()
                    print("Playback Finished.")


def baidu_voice_rec(lang="zh"):
    yes = input("输入yes按Enter开始录制，输入no取消，录制过程中Ctrl-C结束录制：")
    if yes.lower() == "yes":
        _record()
        token = get_token()
        mac = get_mac_address()
        wavfile = open(WAVE_OUTPUT_FILENAME, "rb")
        content = wavfile.read()
        wavlen = len(content)
        wavfile.close()
        r = requests.post("http://vop.baidu.com/server_api?lan=%s&cuid=%s&token=%s" % (lang, mac, token), data=content,
                          headers={"content-type": "audio/wav;rate=%s" % RATE, "content-length": wavlen})
        ret = json.loads(r.text)
        if ret['err_no'] == 0:
            return ret['result']
        else:
            return "识别错误： %s, %s" % (ret['err_no'], ret['err_msg'])
    else:
        return False


def _record():
    global p
    global stream
    global frames
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    print("正在录制...")
    frames = []
    signal.signal(signal.SIGINT, stop_record)
    while (True):
        if stream.is_stopped():
            stream.close()
            p.terminate()
            break
        data = stream.read(CHUNK)
        frames.append(data)


def stop_record(a1, a2):
    stream.stop_stream()
    print("录制结束")
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()


def ctrlc_quit(arg1, arg2):
    print("Ctrl-C Detected. Quiting...")
    sys.exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, ctrlc_quit)
    if len(sys.argv) < 2:
        print("Usage: voice.py speak/hear.")
    else:
        if len(sys.argv) < 3 and sys.argv[1] == "speak":
            print("提示：输入要合成的语句，按Enter开始合成！（输入/quit退出）")
            while (True):
                words = input()
                if words == '/quit':
                    print("Quiting...")
                    sys.exit(0)
                get_baidu_voice(words, person=1)
        elif len(sys.argv) < 3 and sys.argv[1] == "hear":
            print(baidu_voice_rec())
        elif sys.argv[1] == "speak":
            args = " ".join(sys.argv[2:])
            get_baidu_voice(args, person=1)
        else:
            print("Usage: voice.py speak/hear.")

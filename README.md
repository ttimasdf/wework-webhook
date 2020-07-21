# wework-webhook: 使用 Webhook 推送消息至企业微信自建应用

实现效果：使用企业微信的“自建应用”功能替代简陋的Webhook推送通知，能够在微信中查看推送消息内容（Webhook机器人的消息只能在企业微信中看到），简化应用消息开发流程，方便工具脚本接入。

这个服务原本设计就考虑到了可以部署为serverless函数，用户可以自行尝试。作者没有给出配置方法的原因是：阿里云函数计算不好用（TLS配置麻烦），腾讯云函数计算不支持tablestore的某些依赖，会遇到（售后工程师无法解决的）运行时错误。可访问性与暴露服务的安全性问题。

因此建议在家庭内网中自行部署，项目附带的Dockerfile可以在树莓派上成功构建并运行。

![](https://z.cdn.rabit.pw/imgs/2020/20200721113940.jpg)

## 填写配置文件

使用阿里云 TableStore （免费额度非常够用）存储登录状态，请自行创建应用并获取配置信息。

在企业微信管理后台新建应用并获取 AgentID 与 Secret，填入 `config.py` 中。 `config.example.py` 可以作为示例。

## 构建并启动服务

```sh
# Build
docker build . --force-rm -t weworkhook
# Run
docker run -d --restart=always -p 8000:8000 --name hook weworkhook
```

## Webhook 调用

### HTTP 调用

以 httpie 举例。

```sh
$ http -v POST http://127.0.0.1:8000/wework/1000001/text X-WW-Auth:$key content=test
POST /wework/1000001/text HTTP/1.1
Accept: application/json, */*
Accept-Encoding: gzip, deflate
Connection: keep-alive
Content-Length: 19
Content-Type: application/json
Host: 127.0.0.1:8000
User-Agent: HTTPie/1.0.3
X-WW-Auth: *REDACTED*

{
    "content": "test"
}

HTTP/1.1 200 OK
Connection: close
Date: Tue, 21 Jul 2020 03:49:54 GMT
Server: gunicorn/20.0.4
content-length: 49
content-type: application/json

{
    "errcode": 0,
    "errmsg": "ok",
    "invaliduser": ""
}
```

### Home Assistant 调用

1. 在配置文件中新建 `rest_command` 组件，内容如下。
2. 在 `secrets.yaml` 中新增名为 `ww_auth_token` 的密钥，填入 `API_AUTH_KEY` 的值。
3. 在其他 automation 中调用 `rest_command.wxwork` ，调用参数 `msg` 中加入推送消息内容即可。

```yaml
rest_command:
  wxwork:
    url: 'http://localhost:8000/wework/1000001/text'
    method: POST
    headers: { "X-WW-Auth": !secret ww_auth_token }
    content_type: 'application/json; charset=utf-8'
    payload: >
      {
        "content": "{{ msg }}"
      }

  wxwork_md:
    url: 'http://localhost:8000/wework/1000001/md'
    method: POST
    headers: { "X-WW-Auth": !secret ww_auth_token }
    content_type: 'application/json; charset=utf-8'
    payload: >
      {
        "content": "{{ msg }}"
      }
```
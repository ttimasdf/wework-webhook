import falcon
from falcon import Request, Response, API
from wechatpy.enterprise import WeChatClient as WeWorkClient

from utils.tablestorage import TableStorage
from config import (
    OTS_ENDPOINT, OTS_ID, OTS_SECRET, OTS_INSTANCE, OTS_TABLE,
    API_AUTH_KEY,
    WEWORK_CORP_ID, WEWORK_APP_SECRETS,
)


def validate_auth_key(req: Request, resp: Response, resource, params, header, header_value):
    if req.get_header(header) != header_value:
        raise falcon.HTTPUnauthorized()

def validate_app_id(req: Request, resp: Response, resource, params, param="app_id"):
    if params[param] not in WEWORK_APP_SECRETS:
        raise falcon.HTTPNotFound(description="app not found")


@falcon.before(validate_auth_key, "X-WW-Auth", API_AUTH_KEY)
class WeworkAppMsg:
    def __init__(self):
        # 一个App的token初始化一个client。
        self.clients = {}
        # 使用阿里云 TableStorage 存储登陆状态
        self._session_storage = TableStorage(
            OTS_ENDPOINT, OTS_ID, OTS_SECRET, OTS_INSTANCE,
            OTS_TABLE)

    def _get_client(self, app_id=None, app_secret=None):
        """
        根据token获取对应client
        """
        if not app_secret:
            app_secret = WEWORK_APP_SECRETS[app_id]
        if app_secret in self.clients:
            return self.clients[app_secret]
        c = WeWorkClient(WEWORK_CORP_ID, app_secret, session=self._session_storage)
        self.clients[app_secret] = c
        return c

    @falcon.before(validate_app_id)
    def on_post(self, req: Request, resp: Response, app_id, msg_type):
        """
        POST请求处理函数，
        URL path参数：app_id msg_type
        """
        if msg_type not in ["text", "card", "md", "image"]:
            raise falcon.HTTPInvalidParam("should be text/card/md", "msg_type")

        client = self._get_client(app_id)
        groups = req.get_param_as_list("groups", default=[])
        tags = req.get_param_as_list("tags", default=[])
        users = req.get_param_as_list("users", default="@all" if not groups and not tags else [])

        if msg_type == "text":
            content = req.media["content"]
            resp.media = client.message.send_text(
                app_id, users, content,
                party_ids=groups, tag_ids=tags)

        elif msg_type == "markdown":
            content = req.media["content"]
            resp.media = client.message.send_markdown(
                app_id, users, content,
                party_ids=groups, tag_ids=tags)
        elif msg_type == "image":
            if req.content_type == falcon.MEDIA_JSON:
                resp_upload = req.media
            else:
                resp_upload = client.media.upload("image", req.bounded_stream)
            media_id = resp_upload["media_id"]
            resp_post = client.message.send(
                app_id, users,  party_ids=groups, tag_ids=tags,
                msg={"msgtype": "image", "image": {"media_id": media_id}})
            resp_post["media"] = resp_upload
            resp.media = resp_post
        else:
            raise falcon.HTTPNotImplemented(description="I'm lazy")


class WeWorkMenu(WeworkAppMsg):
    @falcon.before(validate_app_id)
    def on_get(self, req: Request, resp: Response, app_id):
        client = self._get_client(app_id)

        resp.media = client.menu.get(app_id)

    @falcon.before(validate_app_id)
    def on_post(self, req: Request, resp: Response, app_id):
        client = self._get_client(app_id)

        resp.media = client.menu.create(app_id, req.media)

    @falcon.before(validate_app_id)
    def on_delete(self, req: Request, resp: Response, app_id):
        client = self._get_client(app_id)

        resp.media = client.menu.delete(app_id)


application = app = API()
# app.add_route('/quote', QuoteResource())
app.add_route("/wework/{app_id}/menu", WeWorkMenu())
app.add_route('/wework/{app_id}/{msg_type}', WeworkAppMsg())
# app.add_sink(orphan)

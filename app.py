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


@falcon.before(validate_auth_key, "X-WW-Auth", API_AUTH_KEY)
class WeworkAppMsg:
    def __init__(self):
        # 一个App的token初始化一个client。
        self.clients = {}
        # 使用阿里云 TableStorage 存储登陆状态
        self._session_storage = TableStorage(
            OTS_ENDPOINT, OTS_ID, OTS_SECRET, OTS_INSTANCE,
            OTS_TABLE)

    def _get_client(self, app_secret):
        """
        根据token获取对应client
        """
        if app_secret in self.clients:
            return self.clients[app_secret]
        c = WeWorkClient(WEWORK_CORP_ID, app_secret, session=self._session_storage)
        self.clients[app_secret] = c
        return c
    

    def on_post(self, req: Request, resp: Response, app_id, msg_type):
        """
        POST请求处理函数，
        URL path参数：app_id msg_type
        """
        app_secret = WEWORK_APP_SECRETS.get(app_id)
        if not app_secret:
            raise falcon.HTTPNotFound(description="app not found")
        if msg_type not in ["text", "card", "md"]:
            raise falcon.HTTPInvalidParam("should be text/card/md", "msg_type")

        groups = req.get_param_as_list("groups", default=[])
        tags = req.get_param_as_list("tags", default=[])
        users = req.get_param_as_list("users", default="@all" if not groups and not tags else [])

        if msg_type == "text":
            content = req.media["content"]
            resp.media = self._get_client(app_secret).message.send_text(
                app_id, users, content,
                party_ids=groups, tag_ids=tags)

        if msg_type == "markdown":
            content = req.media["content"]
            resp.media = self._get_client(app_secret).message.send_markdown(
                app_id, users, content,
                party_ids=groups, tag_ids=tags)


application = app = API()
# app.add_route('/quote', QuoteResource())
app.add_route('/wework/{app_id}/{msg_type}', WeworkAppMsg())
# app.add_sink(orphan)

from tablestore import OTSClient, Row, TableMeta, TableOptions, ReservedThroughput, CapacityUnit
from tablestore.error import OTSServiceError
from wechatpy.session import SessionStorage

# Reference:
# https://github.com/jxtech/wechatpy/blob/master/wechatpy/session/shovestorage.py
# https://github.com/aliyun/aliyun-tablestore-python-sdk/blob/master/examples/put_row.py
# https://github.com/aliyun/aliyun-tablestore-python-sdk/blob/master/examples/get_row.py


class TableStorage(SessionStorage):

    def __init__(self, ots_endpoint, ots_id, ots_secret, ots_instance, table_name, col_key="key", col_value="value", cache=False):
        self.client = OTSClient(ots_endpoint, ots_id, ots_secret, ots_instance)
        self.table = table_name
        self._k = col_key
        self._v = col_value
        self._c = cache
        self._data = {}

    def create_table(self):
        table_meta = TableMeta(self.table, [(self._k, 'STRING')])
        options = TableOptions(time_to_live=3600 * 24 * 7)
        self.client.create_table(table_meta, options, ReservedThroughput(CapacityUnit(0, 0)))

    def get(self, key, default=None):
        if self._c and key in self._data:
            return self._data["key"]
        primary_key = [(self._k, key)]
        try:
            consumed, row, _ = self.client.get_row(self.table, primary_key, [self._v])
        except OTSServiceError as e:
            self.create_table()
            consumed, row, _ = self.client.get_row(self.table, primary_key, [self._v])
        # print(f"getting key: {primary_key}, consume: R:{consumed.read} W:{consumed.write}, attrs: {row.attribute_columns}")
        if row is None:
            return default
        for k, v, timestamp in row.attribute_columns:
            if k == self._v:
                return v
        return default

    def set(self, key, value, ttl=None):
        primary_key = [(self._k, key)]
        row = Row(primary_key, [(self._v, value)])
        consumed, row = self.client.put_row(self.table, row)
        if self._c:
            self._data[key] = value
        # print(f"set key: {key}, value: {value}, consume: R:{consumed.read} W:{consumed.write}")

    def delete(self, key):
        primary_key = [(self._k, key)]
        row = Row(primary_key)
        consumed, row = self.client.delete_row(self.table, row)
        if self._c:
            self._data.pop(key, None)

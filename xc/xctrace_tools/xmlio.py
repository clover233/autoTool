"""xctrace 表格读取，统一处理 schema 和链式 id/ref 引用。"""

from pathlib import Path
import xml.etree.ElementTree as ET


def build_id_map(root):
    return {element.get('id'): element for element in root.iter() if element.get('id')}


def resolve_element(element, references):
    if element is None:
        raise ValueError('缺少 XML 元素')
    seen = set()
    while element.get('ref'):
        ref = element.get('ref')
        if ref in seen or ref not in references:
            raise ValueError(f'无效 XML ref: {ref}')
        seen.add(ref)
        element = references[ref]
    return element


def process_name(element):
    return element.get('fmt', '').rsplit(' (', 1)[0].strip()


class TraceTable:
    def __init__(self, path, schema_name=None):
        self.path = Path(path)
        self.tree = ET.parse(self.path)
        self.root = self.tree.getroot()
        nodes = [node for node in self.root.iter('node')
                 if node.find('schema') is not None
                 and (schema_name is None or node.find('schema').get('name') == schema_name)]
        if len(nodes) != 1:
            raise ValueError(f'应有且仅有一个 {schema_name or "schema"} 数据表，实际 {len(nodes)} 个')
        self.node = nodes[0]
        self.schema = {}
        for column in self.node.find('schema').findall('col'):
            mnemonic = column.findtext('mnemonic')
            if not mnemonic or mnemonic in self.schema:
                raise ValueError(f'无效或重复的 schema 列: {mnemonic}')
            self.schema[mnemonic] = {'name': column.findtext('name', mnemonic),
                                     'type': column.findtext('engineering-type', '')}
        if not self.schema:
            raise ValueError('XML schema 没有数据列')
        self.references = build_id_map(self.root)

    def require(self, *columns):
        for column in columns:
            if column not in self.schema:
                raise ValueError(f'缺少列: {column}')

    def resolve(self, element):
        return resolve_element(element, self.references)

    def rows(self):
        for index, row in enumerate(self.node.findall('row'), 1):
            children = list(row)
            if len(children) != len(self.schema):
                raise ValueError(f'第 {index} 行有 {len(children)} 列，schema 定义了 {len(self.schema)} 列')
            yield dict(zip(self.schema, children))

    def value(self, element):
        element = self.resolve(element)
        if element.tag in ('start-time', 'size-in-bytes'):
            return int(element.text or '')
        if element.tag == 'process':
            name = process_name(element)
            if not name:
                raise ValueError('进程名为空')
            return name
        return element.text or ''

    def records(self, columns=None):
        selected = set(columns) if columns else set(self.schema)
        self.require(*selected)
        return [{name: self.value(element) for name, element in row.items() if name in selected}
                for row in self.rows()]

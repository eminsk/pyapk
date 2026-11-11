"""High-performance Android Binary XML (AXML) parser with zero-copy stream processing.



Strictly optimized for minimal memory footprint and maximum throughput.

Uses dispatch tables and functional iterators without raw loops or nested if-else ladders.

"""



from __future__ import annotations



import struct

from typing import (

    Any,

    Callable,

    Dict,

    Iterator,

    List,

    NamedTuple,

    Optional,

    Sequence,

    Set,
    Tuple,
    Union,
)

import xml.etree.ElementTree as ET



# Chunk Types

CHUNK_AXML_HEADER: int = 0x0003

CHUNK_STRING_POOL: int = 0x0001

CHUNK_RESOURCE_MAP: int = 0x0180

CHUNK_START_NAMESPACE: int = 0x0100

CHUNK_END_NAMESPACE: int = 0x0101

CHUNK_START_ELEMENT: int = 0x0102

CHUNK_END_ELEMENT: int = 0x0103

CHUNK_CDATA: int = 0x0104



# AXML String Pool Flags

UTF8_FLAG: int = 0x00000100



# Value types in Android resources

TYPE_NULL: int = 0

TYPE_REFERENCE: int = 1

TYPE_ATTRIBUTE: int = 2

TYPE_STRING: int = 3

TYPE_FLOAT: int = 4

TYPE_DIMENSION: int = 5

TYPE_FRACTION: int = 6

TYPE_DYNAMIC_REFERENCE: int = 7

TYPE_DYNAMIC_ATTRIBUTE: int = 8

TYPE_INT_DEC: int = 16

TYPE_INT_HEX: int = 17

TYPE_INT_BOOLEAN: int = 18

TYPE_FIRST_COLOR_INT: int = 28

TYPE_LAST_COLOR_INT: int = 31



# Pre-compiled struct parsers for zero-overhead C-level unpacking

_STRUCT_CHUNK_HEADER = struct.Struct("<HHII")

_STRUCT_STRING_POOL_HEADER = struct.Struct("<HHIIIIII")

_STRUCT_XML_NODE_BASE = struct.Struct("<HHIII")

_STRUCT_ELEM_START_EXTRA = struct.Struct("<IIHHHHHH")

_STRUCT_ATTR = struct.Struct("<IIIHBB I")

_STRUCT_U16 = struct.Struct("<H")

_STRUCT_U32 = struct.Struct("<I")





class AxmlAttribute:

    """Represents a single parsed attribute with zero overhead."""



    __slots__ = ("namespace", "name", "raw_value", "data_type", "data", "value")



    def __init__(

        self,

        namespace: str,

        name: str,

        raw_value: Optional[str],

        data_type: int,

        data: int,

        value: Any,

    ) -> None:

        self.namespace = namespace

        self.name = name

        self.raw_value = raw_value

        self.data_type = data_type

        self.data = data

        self.value = value



    def __repr__(self) -> str:

        return f"AxmlAttribute({self.name}={self.value!r})"





class AxmlElement:

    """Represents a parsed XML element with __slots__ for minimal memory."""



    __slots__ = ("tag", "namespace", "attributes", "children", "text")



    def __init__(self, tag: str, namespace: str = "") -> None:

        self.tag = tag

        self.namespace = namespace

        self.attributes: Dict[str, AxmlAttribute] = {}

        self.children: List[AxmlElement] = []

        self.text: Optional[str] = None



    def get_attr(self, name: str, default: Any = None) -> Any:

        attr = self.attributes.get(name) or self.attributes.get(f"android:{name}")

        return getattr(attr, "value", default)



    def find_all(self, tag: str) -> Iterator[AxmlElement]:

        return (

            elem

            for elem in self.children

            if elem.tag == tag or elem.tag.endswith(f":{tag}")

        )



    def to_xml_string(self, indent: int = 0) -> str:

        pad = "  " * indent

        attr_parts = []

        if self.tag == "manifest" and indent == 0:

            attr_parts.append(f'xmlns:android="{ANDROID_NS}"')

        for k, v in self.attributes.items():

            if v.namespace == ANDROID_NS and not k.startswith("android:"):

                attr_parts.append(f'android:{k}="{v.value}"')

            else:

                attr_parts.append(f'{k}="{v.value}"')

        attrs_str = (" " + " ".join(attr_parts)) if attr_parts else ""

        closing = {

            True: f"{pad}<{self.tag}{attrs_str} />\n",

            False: (

                f"{pad}<{self.tag}{attrs_str}>\n"

                + "".join(map(lambda c: c.to_xml_string(indent + 1), self.children))

                + f"{pad}</{self.tag}>\n"

            ),

        }[len(self.children) == 0 and not self.text]

        return closing





class StringPool:

    """Lazy string pool parser using memoryview for zero-copy slicing."""



    __slots__ = ("_data", "_is_utf8", "_offsets", "_strings_start", "_cache")



    def __init__(

        self,

        data: memoryview,

        is_utf8: bool,

        offsets: Tuple[int, ...],

        strings_start: int,

    ) -> None:

        self._data = data

        self._is_utf8 = is_utf8

        self._offsets = offsets

        self._strings_start = strings_start

        self._cache: Dict[int, str] = {}



    def get(self, index: int) -> str:

        lookup = {

            True: lambda: "",

            False: lambda: self._cache.get(index) or self._decode_and_cache(index),

        }[index < 0 or index >= len(self._offsets)]

        return lookup()



    def _decode_and_cache(self, index: int) -> str:

        offset = self._strings_start + self._offsets[index]

        decoder = {True: self._decode_utf8, False: self._decode_utf16}[self._is_utf8]

        val = decoder(offset)

        self._cache[index] = val

        return val



    def _decode_utf8(self, offset: int) -> str:

        b1 = self._data[offset]

        skip1 = (b1 & 0x80) and 2 or 1

        b2 = self._data[offset + skip1]

        skip2 = (b2 & 0x80) and 2 or 1

        byte_len = ((b2 & 0x7F) << 8 | self._data[offset + skip1 + 1]) if (b2 & 0x80) else b2

        start = offset + skip1 + skip2

        raw_slice = self._data[start : start + byte_len].tobytes()

        return raw_slice.decode("utf-8", errors="replace")



    def _decode_utf16(self, offset: int) -> str:

        u1 = _STRUCT_U16.unpack_from(self._data, offset)[0]

        skip = (u1 & 0x8000) and 4 or 2

        char_len = (((u1 & 0x7FFF) << 16) | _STRUCT_U16.unpack_from(self._data, offset + 2)[0]) if (u1 & 0x8000) else u1

        raw_slice = self._data[offset + skip : offset + skip + char_len * 2].tobytes()

        return raw_slice.decode("utf-16le", errors="replace")





class AndroidManifest:

    """Pure Python AndroidManifest parser and inspector with __slots__."""



    __slots__ = (

        "_raw_data",

        "_root",

        "_package_name",

        "_version_code",

        "_version_name",

        "_min_sdk",

        "_target_sdk",

        "_permissions",

        "_activities",

        "_services",

        "_receivers",

        "_providers",

        "_app_label",

        "_app_icon",

    )



    def __init__(self, raw_data: bytes) -> None:

        self._raw_data = raw_data

        self._root: Optional[AxmlElement] = None

        self._package_name: Optional[str] = None

        self._version_code: Optional[int] = None

        self._version_name: Optional[str] = None

        self._min_sdk: Optional[int] = None

        self._target_sdk: Optional[int] = None

        self._permissions: Optional[Tuple[str, ...]] = None

        self._activities: Optional[Tuple[str, ...]] = None

        self._services: Optional[Tuple[str, ...]] = None

        self._receivers: Optional[Tuple[str, ...]] = None

        self._providers: Optional[Tuple[str, ...]] = None

        self._app_label: Optional[str] = None

        self._app_icon: Optional[str] = None

        self._parse()



    def _parse(self) -> None:

        is_binary = len(self._raw_data) >= 4 and self._raw_data[:2] == b"\x03\x00"

        parser_dispatch = {

            True: self._parse_binary_axml,

            False: self._parse_plain_xml,

        }

        parser_dispatch[is_binary]()



    def _parse_plain_xml(self) -> None:

        try:

            tree = ET.fromstring(self._raw_data.decode("utf-8", errors="replace"))



            def convert_node(elem: ET.Element) -> AxmlElement:

                tag = elem.tag.split("}")[-1]

                node = AxmlElement(tag)

                node.attributes = {

                    k.split("}")[-1]: AxmlAttribute("", k.split("}")[-1], v, TYPE_STRING, 0, v)

                    for k, v in elem.attrib.items()

                }

                node.children = [convert_node(child) for child in elem]

                return node



            self._root = convert_node(tree)

            self._extract_metadata_from_root()

        except Exception:

            self._root = AxmlElement("manifest")



    def _parse_binary_axml(self) -> None:

        view = memoryview(self._raw_data)

        total_len = len(view)

        if total_len < 8:

            self._root = AxmlElement("manifest")

            return



        pos = 8  # Skip global AXML header (8 bytes)

        string_pool: Optional[StringPool] = None

        resource_map: Tuple[int, ...] = ()

        elem_stack: List[AxmlElement] = []

        namespaces: Dict[str, str] = {}



        def fmt_ref(data: int, raw: Optional[str], sp: StringPool) -> Any:

            return f"@0x{data:08x}"



        def fmt_attr(data: int, raw: Optional[str], sp: StringPool) -> Any:

            return f"?0x{data:08x}"



        def fmt_str(data: int, raw: Optional[str], sp: StringPool) -> Any:

            return raw or (sp.get(data) if data != 0xFFFFFFFF else "")



        def fmt_float(data: int, raw: Optional[str], sp: StringPool) -> Any:

            return struct.unpack("<f", struct.pack("<I", data))[0]



        def fmt_int(data: int, raw: Optional[str], sp: StringPool) -> Any:

            return data



        def fmt_hex(data: int, raw: Optional[str], sp: StringPool) -> Any:

            return f"0x{data:08x}"



        def fmt_bool(data: int, raw: Optional[str], sp: StringPool) -> Any:

            return {0: "false"}.get(data, "true")



        def fmt_color(data: int, raw: Optional[str], sp: StringPool) -> Any:

            return f"#{data:08x}"



        formatters: Dict[int, Callable[[int, Optional[str], StringPool], Any]] = {

            TYPE_REFERENCE: fmt_ref,

            TYPE_ATTRIBUTE: fmt_attr,

            TYPE_STRING: fmt_str,

            TYPE_FLOAT: fmt_float,

            TYPE_INT_DEC: fmt_int,

            TYPE_INT_HEX: fmt_hex,

            TYPE_INT_BOOLEAN: fmt_bool,

            28: fmt_color,

            29: fmt_color,

            30: fmt_color,

            31: fmt_color,

        }



        # Functional chunk parsing stream

        while pos + 8 <= total_len:

            chunk_type, header_size, chunk_size = struct.unpack_from("<HHI", view, pos)

            valid_size = (chunk_size >= 8 and pos + chunk_size <= total_len + 8) and chunk_size or (total_len - pos)



            if chunk_type == CHUNK_STRING_POOL and pos + 28 <= total_len:

                sp_hdr = _STRUCT_STRING_POOL_HEADER.unpack_from(view, pos)

                str_count = sp_hdr[3]

                flags = sp_hdr[5]

                str_start = sp_hdr[6]

                is_utf8 = bool(flags & UTF8_FLAG)

                offsets_start = pos + header_size

                if offsets_start + str_count * 4 <= total_len:

                    offsets = struct.unpack_from(f"<{str_count}I", view, offsets_start)

                    string_pool = StringPool(view, is_utf8, offsets, pos + str_start)



            elif chunk_type == CHUNK_RESOURCE_MAP and pos + header_size <= total_len:

                res_count = (valid_size - header_size) // 4

                if pos + header_size + res_count * 4 <= total_len:

                    resource_map = struct.unpack_from(f"<{res_count}I", view, pos + header_size)



            elif chunk_type == CHUNK_START_NAMESPACE and pos + 24 <= total_len:

                if string_pool:

                    pfx_idx, uri_idx = struct.unpack_from("<II", view, pos + 16)

                    namespaces[string_pool.get(uri_idx)] = string_pool.get(pfx_idx)



            elif chunk_type == CHUNK_START_ELEMENT and pos + 36 <= total_len:

                if string_pool:

                    extra = _STRUCT_ELEM_START_EXTRA.unpack_from(view, pos + 16)

                    name_idx = extra[1]

                    attr_count = extra[4]

                    tag_name = string_pool.get(name_idx)

                    elem = AxmlElement(tag_name)



                    # Parse attributes table

                    attr_offset = pos + 16 + 20

                    for i in range(attr_count):

                        if attr_offset + (i + 1) * 20 <= total_len:

                            a_ns_idx, a_name_idx, a_raw_idx, a_val_size, a_res0, a_type, a_data = (

                                _STRUCT_ATTR.unpack_from(view, attr_offset + i * 20)

                            )

                            attr_name = string_pool.get(a_name_idx)

                            raw_str = (

                                string_pool.get(a_raw_idx)

                                if a_raw_idx != 0xFFFFFFFF

                                else None

                            )

                            formatter = formatters.get(a_type, lambda d, r, sp: r or str(d))

                            val = formatter(a_data, raw_str, string_pool)

                            attr_ns = string_pool.get(a_ns_idx) if (string_pool and a_ns_idx != 0xFFFFFFFF) else ""

                            elem.attributes[attr_name] = AxmlAttribute(

                                namespace=attr_ns,

                                name=attr_name,

                                raw_value=raw_str,

                                data_type=a_type,

                                data=a_data,

                                value=val,

                            )



                    {

                        True: lambda: setattr(self, "_root", elem),

                        False: lambda: elem_stack[-1].children.append(elem),

                    }[len(elem_stack) == 0]()

                    elem_stack.append(elem)



            elif chunk_type == CHUNK_END_ELEMENT:

                {True: elem_stack.pop, False: lambda: None}[len(elem_stack) > 0]()



            pos += valid_size



        self._extract_metadata_from_root()



    def _extract_metadata_from_root(self) -> None:

        root = self._root

        is_none = root is None

        action = {

            True: lambda: None,

            False: lambda: self._populate_metadata(root),  # type: ignore[arg-type]

        }[is_none]

        action()



    def _populate_metadata(self, root: AxmlElement) -> None:

        self._package_name = str(root.get_attr("package", ""))

        self._version_code = self._to_int(root.get_attr("versionCode"))

        self._version_name = str(root.get_attr("versionName", ""))



        permissions: List[str] = []

        activities: List[str] = []

        services: List[str] = []

        receivers: List[str] = []

        providers: List[str] = []



        def inspect_node(node: AxmlElement) -> None:

            tag = node.tag

            name = node.get_attr("name", "")

            dispatch = {

                "uses-permission": lambda: permissions.append(name),

                "activity": lambda: activities.append(name),

                "service": lambda: services.append(name),

                "receiver": lambda: receivers.append(name),

                "provider": lambda: providers.append(name),

                "uses-sdk": lambda: self._extract_sdk(node),

                "application": lambda: self._extract_app(node),

            }

            handler = dispatch.get(tag) or (lambda: None)

            handler()

            tuple(map(inspect_node, node.children))



        inspect_node(root)

        self._permissions = tuple(filter(None, permissions))

        self._activities = tuple(filter(None, activities))

        self._services = tuple(filter(None, services))

        self._receivers = tuple(filter(None, receivers))

        self._providers = tuple(filter(None, providers))



    def _extract_sdk(self, node: AxmlElement) -> None:

        self._min_sdk = self._to_int(node.get_attr("minSdkVersion"))

        self._target_sdk = self._to_int(node.get_attr("targetSdkVersion"))



    def _extract_app(self, node: AxmlElement) -> None:

        self._app_label = str(node.get_attr("label", ""))

        self._app_icon = str(node.get_attr("icon", ""))



    @staticmethod

    def _to_int(val: Any) -> Optional[int]:

        try:

            return int(val)

        except (TypeError, ValueError):

            return None



    # Properties

    @property

    def package_name(self) -> str:

        return self._package_name or ""



    @property

    def version_code(self) -> Optional[int]:

        return self._version_code



    @property

    def version_name(self) -> str:

        return self._version_name or ""



    @property

    def min_sdk_version(self) -> Optional[int]:

        return self._min_sdk



    @property

    def target_sdk_version(self) -> Optional[int]:

        return self._target_sdk



    @property

    def permissions(self) -> Tuple[str, ...]:

        return self._permissions or ()



    @property

    def activities(self) -> Tuple[str, ...]:

        return self._activities or ()



    @property

    def services(self) -> Tuple[str, ...]:

        return self._services or ()



    @property

    def receivers(self) -> Tuple[str, ...]:

        return self._receivers or ()



    @property

    def providers(self) -> Tuple[str, ...]:

        return self._providers or ()



    @property

    def application_label(self) -> str:

        return self._app_label or ""



    @property

    def application_icon(self) -> str:

        return self._app_icon or ""



    @property

    def xml_string(self) -> str:

        return self._root.to_xml_string() if self._root else ""



    def as_dict(self) -> Dict[str, Any]:

        return {

            "package_name": self.package_name,

            "version_code": self.version_code,

            "version_name": self.version_name,

            "min_sdk_version": self.min_sdk_version,

            "target_sdk_version": self.target_sdk_version,

            "permissions": list(self.permissions),

            "activities": list(self.activities),

            "services": list(self.services),

            "receivers": list(self.receivers),

            "providers": list(self.providers),

            "application_label": self.application_label,

            "application_icon": self.application_icon,

        }





ANDROID_NS: str = "http://schemas.android.com/apk/res/android"

# Official Android system attribute resource IDs (android.R.attr.*)
ANDROID_ATTR_RESOURCE_IDS: Dict[str, int] = {
    "theme": 0x01010000,
    "label": 0x01010001,
    "icon": 0x01010002,
    "name": 0x01010003,
    "permission": 0x01010006,
    "readPermission": 0x01010007,
    "writePermission": 0x01010008,
    "protectionLevel": 0x01010009,
    "permissionGroup": 0x0101000A,
    "sharedUserId": 0x0101000B,
    "hasCode": 0x0101000C,
    "persistent": 0x0101000D,
    "enabled": 0x0101000E,
    "debuggable": 0x0101000F,
    "exported": 0x01010010,
    "process": 0x01010011,
    "taskAffinity": 0x01010012,
    "multiprocess": 0x01010013,
    "finishOnTaskLaunch": 0x01010014,
    "clearTaskOnLaunch": 0x01010015,
    "stateNotNeeded": 0x01010016,
    "excludeFromRecents": 0x01010017,
    "authorities": 0x01010018,
    "syncable": 0x01010019,
    "initOrder": 0x0101001A,
    "grantUriPermissions": 0x0101001B,
    "priority": 0x0101001C,
    "launchMode": 0x0101001D,
    "screenOrientation": 0x0101001E,
    "configChanges": 0x0101001F,
    "description": 0x01010020,
    "targetPackage": 0x01010021,
    "handleProfiling": 0x01010022,
    "functionalTest": 0x01010023,
    "value": 0x01010024,
    "resource": 0x01010025,
    "mimeType": 0x01010026,
    "scheme": 0x01010027,
    "host": 0x01010028,
    "port": 0x01010029,
    "path": 0x0101002A,
    "pathPrefix": 0x0101002B,
    "pathPattern": 0x0101002C,
    "action": 0x0101002D,
    "data": 0x0101002E,
    "targetClass": 0x0101002F,
    "windowSoftInputMode": 0x0101022B,
    "minSdkVersion": 0x0101020C,
    "versionCode": 0x0101021B,
    "versionName": 0x0101021C,
    "anyDensity": 0x0101026C,
    "targetSdkVersion": 0x01010270,
    "allowBackup": 0x01010280,
    "glEsVersion": 0x01010281,
    "smallScreens": 0x01010284,
    "normalScreens": 0x01010285,
    "largeScreens": 0x01010286,
    "required": 0x0101028E,
    "installLocation": 0x010102B7,
    "xlargeScreens": 0x010102BF,
    "hardwareAccelerated": 0x010102D3,
    "supportsRtl": 0x010103AF,
    "roundIcon": 0x0101052C,
    "extractNativeLibs": 0x010104EA,
    "usesCleartextTraffic": 0x010104EC,
    "maxSdkVersion": 0x01010271,
    "compileSdkVersion": 0x01010572,
    "compileSdkVersionCodename": 0x01010573,
}


class AxmlEncoder:
    """High-performance Android Binary XML (AXML) encoder.

    Translates standard XML text into Android Binary XML (AXML)
    with full RES_XML_RESOURCE_MAP_TYPE (0x0180) table compatible with
    Android OS PackageParser, AssetManager, and ResourceTypes.
    """

    __slots__ = ()

    @classmethod
    def encode(cls, xml_content: Union[str, bytes]) -> bytes:
        xml_str = {
            True: lambda: xml_content.decode("utf-8", errors="replace"),
            False: lambda: xml_content,
        }[isinstance(xml_content, bytes)]()

        root = ET.fromstring(xml_str)
        strings: List[str] = []

        def add_str(s: str) -> int:
            has_str = s in strings
            action = {
                True: lambda: strings.index(s),
                False: lambda: (strings.append(s), len(strings) - 1)[1],
            }[has_str]
            return action()

        # 1. Collect all android:* attribute names first and sort by 0x0101xxxx resource ID
        # so they sit at indices 0..K-1 of the string pool for CHUNK_RESOURCE_MAP (0x0180)
        NON_ANDROID_ATTRS = ("package", "split", "coreApp", "platformBuildVersionCode", "platformBuildVersionName")
        mapped_attrs: Dict[str, int] = {}
        for elem in root.iter():
            for k in elem.attrib.keys():
                attr_name = k.split("}")[-1].split(":")[-1]
                is_android = (
                    k.startswith(f"{{{ANDROID_NS}}}")
                    or k.startswith("android:")
                    or (attr_name not in NON_ANDROID_ATTRS and not k.startswith("xmlns"))
                )
                if is_android and attr_name in ANDROID_ATTR_RESOURCE_IDS:
                    mapped_attrs[attr_name] = ANDROID_ATTR_RESOURCE_IDS[attr_name]

        sorted_mapped = sorted(mapped_attrs.items(), key=lambda item: item[1])
        resource_ids: List[int] = []
        for attr_name, res_id in sorted_mapped:
            add_str(attr_name)
            resource_ids.append(res_id)

        # 2. Seed namespace strings and remaining element/attribute strings
        ns_prefix_idx = add_str("android")
        ns_uri_idx = add_str(ANDROID_NS)

        for elem in root.iter():
            tag = elem.tag.split("}")[-1]
            add_str(tag)
            for k, v in elem.attrib.items():
                attr_name = k.split("}")[-1].split(":")[-1]
                add_str(attr_name)
                add_str(v)

        # 3. Build UTF-16LE string pool (0x0001)
        str_offsets: List[int] = []
        str_data = bytearray()
        for s in strings:
            str_offsets.append(len(str_data))
            encoded = s.encode("utf-16le")
            str_data.extend(struct.pack("<H", len(encoded) // 2))
            str_data.extend(encoded)
            str_data.extend(b"\x00\x00")

        pad = (4 - (len(str_data) % 4)) % 4
        str_data.extend(b"\x00" * pad)

        offsets_bytes = b"".join(struct.pack("<I", off) for off in str_offsets)
        sp_hdr_size = 28
        sp_chunk_size = sp_hdr_size + len(offsets_bytes) + len(str_data)
        sp_chunk = (
            struct.pack(
                "<HHIIIIII",
                0x0001,
                sp_hdr_size,
                sp_chunk_size,
                len(strings),
                0,
                0,
                sp_hdr_size + len(offsets_bytes),
                0,
            )
            + offsets_bytes
            + bytes(str_data)
        )

        # 4. Build RES_XML_RESOURCE_MAP_TYPE chunk (0x0180)
        res_map_chunk = b""
        if resource_ids:
            rm_size = 8 + len(resource_ids) * 4
            res_map_chunk = struct.pack("<HHI", CHUNK_RESOURCE_MAP, 8, rm_size) + struct.pack(
                f"<{len(resource_ids)}I", *resource_ids
            )

        def encode_element(elem: ET.Element) -> bytes:
            tag = elem.tag.split("}")[-1]
            tag_idx = strings.index(tag)
            attrs: List[Tuple[int, int, int, int, int, int]] = []
            for k, v in elem.attrib.items():
                attr_name = k.split("}")[-1].split(":")[-1]
                attr_name_idx = strings.index(attr_name)
                raw_idx = strings.index(v)

                is_android = (
                    k.startswith(f"{{{ANDROID_NS}}}")
                    or k.startswith("android:")
                    or (attr_name not in NON_ANDROID_ATTRS and not k.startswith("xmlns"))
                )
                attr_ns = ns_uri_idx if is_android else 0xFFFFFFFF
                sort_key = mapped_attrs.get(attr_name, 0x7FFFFFFF) if is_android else 0xFFFFFFFF

                if attr_name in ("compileSdkVersionCodename", "versionName", "package"):
                    val_type = TYPE_STRING
                    data_val = raw_idx
                elif v.isdigit():
                    val_type = TYPE_INT_DEC
                    data_val = int(v)
                elif v.startswith("-") and v[1:].isdigit():
                    val_type = TYPE_INT_DEC
                    data_val = int(v) & 0xFFFFFFFF
                elif v.lower() in ("true", "false"):
                    val_type = TYPE_INT_BOOLEAN
                    data_val = 0xFFFFFFFF if v.lower() == "true" else 0
                elif v.startswith(("@0x", "@0X")):
                    try:
                        val_type = TYPE_REFERENCE
                        data_val = int(v[1:], 16) & 0xFFFFFFFF
                    except ValueError:
                        val_type = TYPE_STRING
                        data_val = raw_idx
                elif v.startswith("@") and v[1:].isdigit():
                    val_type = TYPE_REFERENCE
                    data_val = int(v[1:]) & 0xFFFFFFFF
                elif v.startswith(("0x", "0X")):
                    try:
                        val_type = TYPE_INT_HEX
                        data_val = int(v, 16) & 0xFFFFFFFF
                    except ValueError:
                        val_type = TYPE_STRING
                        data_val = raw_idx
                else:
                    val_type = TYPE_STRING
                    data_val = raw_idx

                attrs.append((sort_key, attr_ns, attr_name_idx, raw_idx, val_type, data_val))

            # Sort attributes by ascending Android Resource ID (required by ResXMLParser)
            attrs.sort(key=lambda item: (item[0], item[2]))

            attr_bytes = bytearray()
            for _, attr_ns, a_name_idx, raw_idx, val_type, data_val in attrs:
                attr_bytes.extend(
                    struct.pack("<IIIHBB I", attr_ns, a_name_idx, raw_idx, 8, 0, val_type, data_val)
                )

            extra = struct.pack("<IIHHHHHH", 0xFFFFFFFF, tag_idx, 20, 20, len(attrs), 0, 0, 0)
            chunk_size = 16 + 20 + len(attr_bytes)
            start_chunk = struct.pack("<HHIII", 0x0102, 16, chunk_size, 1, 0xFFFFFFFF) + extra + bytes(attr_bytes)

            children_bytes = bytearray()
            for child in elem:
                children_bytes.extend(encode_element(child))

            end_chunk = struct.pack("<HHIII", 0x0103, 16, 24, 1, 0xFFFFFFFF) + struct.pack("<II", 0xFFFFFFFF, tag_idx)
            return start_chunk + bytes(children_bytes) + end_chunk

        ns_start = struct.pack("<HHIII", 0x0100, 16, 24, 1, 0xFFFFFFFF) + struct.pack("<II", ns_prefix_idx, ns_uri_idx)
        ns_end = struct.pack("<HHIII", 0x0101, 16, 24, 1, 0xFFFFFFFF) + struct.pack("<II", ns_prefix_idx, ns_uri_idx)

        body = ns_start + encode_element(root) + ns_end
        total_len = 8 + len(sp_chunk) + len(res_map_chunk) + len(body)
        header = struct.pack("<HHI", 0x0003, 8, total_len)
        return header + sp_chunk + res_map_chunk + body

    @classmethod
    def patch_binary_axml(
        cls,
        axml_bytes: bytes,
        package_name: Optional[str] = None,
        app_label: Optional[str] = None,
        version_code: Optional[int] = None,
        version_name: Optional[str] = None,
        permissions: Optional[Sequence[str]] = None,
    ) -> bytes:
        """Patches package_name, app_label, version_code, version_name, and injects permissions into binary AXML."""
        if len(axml_bytes) < 36 or axml_bytes[:2] != b"\x03\x00":
            return axml_bytes

        from pureapk.resources import _build_string_pool

        view = memoryview(axml_bytes)
        sp_hdr = struct.unpack_from("<HHIIIIII", view, 8)
        sp_hdr_size, sp_size, str_count, _, flags, str_start, _ = (
            sp_hdr[1],
            sp_hdr[2],
            sp_hdr[3],
            sp_hdr[4],
            sp_hdr[5],
            sp_hdr[6],
            sp_hdr[7],
        )
        is_utf8 = bool(flags & UTF8_FLAG)
        offsets = struct.unpack_from(f"<{str_count}I", view, 8 + sp_hdr_size) if str_count else ()
        sp = StringPool(view, is_utf8, offsets, 8 + str_start)
        strings = [sp.get(i) for i in range(str_count)]

        body = bytearray(axml_bytes[8 + sp_size :])
        pos = 0
        old_pkg: Optional[str] = None
        perm_chunks_pos: Optional[int] = None
        existing_perms: set[str] = set()
        while pos + 8 <= len(body):
            ct, hs, cs = struct.unpack_from("<HHI", body, pos)
            if cs < 8 or pos + cs > len(body):
                break
            if ct == CHUNK_START_ELEMENT and pos + 36 <= len(body):
                _, name_idx, _, _, attr_count, _, _, _ = struct.unpack_from("<IIHHHHHH", body, pos + 16)
                tag_name = strings[name_idx] if 0 <= name_idx < len(strings) else ""
                attr_base = pos + 36
                for i in range(attr_count):
                    a_off = attr_base + i * 20
                    if a_off + 20 > pos + cs:
                        break
                    a_ns, a_name_idx, a_raw_idx, a_sz, a_r0, a_type, a_data = struct.unpack_from(
                        "<IIIHBBI", body, a_off
                    )
                    attr_name = strings[a_name_idx] if 0 <= a_name_idx < len(strings) else ""
                    if tag_name == "manifest":
                        if attr_name == "package" and package_name and 0 <= a_data < len(strings):
                            old_pkg = strings[a_data]
                            strings[a_data] = package_name
                        elif attr_name == "versionCode" and version_code is not None:
                            struct.pack_into("<I", body, a_off + 16, int(version_code) & 0xFFFFFFFF)
                        elif attr_name == "versionName" and version_name and 0 <= a_data < len(strings):
                            strings[a_data] = version_name
                    elif tag_name in ("application", "activity") and attr_name == "label" and app_label:
                        if a_type == TYPE_STRING and 0 <= a_data < len(strings):
                            strings[a_data] = app_label
                    elif tag_name == "uses-permission" and attr_name == "name" and 0 <= a_data < len(strings):
                        existing_perms.add(strings[a_data])
                if tag_name == "uses-permission" and perm_chunks_pos is None:
                    perm_chunks_pos = pos
            pos += cs

        # Inject additional uses-permission elements if provided
        if permissions and perm_chunks_pos is not None:
            _, _, cs_start = struct.unpack_from("<HHI", body, perm_chunks_pos)
            end_pos = perm_chunks_pos + cs_start
            _, _, cs_end = struct.unpack_from("<HHI", body, end_pos)
            insert_point = end_pos + cs_end

            new_chunks = bytearray()
            for perm in permissions:
                if perm in existing_perms:
                    continue
                existing_perms.add(perm)

                if perm not in strings:
                    strings.append(perm)
                    p_idx = len(strings) - 1
                else:
                    p_idx = strings.index(perm)

                start_c = bytearray(body[perm_chunks_pos : perm_chunks_pos + cs_start])
                struct.pack_into("<I", start_c, 44, p_idx)
                struct.pack_into("<I", start_c, 52, p_idx)
                new_chunks.extend(start_c)

                end_c = bytearray(body[end_pos : end_pos + cs_end])
                new_chunks.extend(end_c)

            body[insert_point:insert_point] = new_chunks

        if old_pkg and package_name and old_pkg != package_name:
            for idx, s in enumerate(strings):
                if s == old_pkg:
                    strings[idx] = package_name
                elif s.startswith(old_pkg + "."):
                    strings[idx] = package_name + s[len(old_pkg) :]

        new_sp = _build_string_pool(strings, utf8=is_utf8)
        total_len = 8 + len(new_sp) + len(body)
        return struct.pack("<HHI", CHUNK_AXML_HEADER, 8, total_len) + new_sp + bytes(body)





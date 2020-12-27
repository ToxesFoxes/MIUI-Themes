import os
import os.path


def get_xml():
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"


def add_single(name, value):
    return "\t<"+name+">"+get_cdata(value)+"</"+name+">\n"


def get_cdata(value):
    return "<![CDATA[" + value + "]]>"


def add_multiple(names, name, obj):
    result = "\t<"+names+">\n"
    for key in obj:
        if(key != "value_name"):
            result += "\t\t<"+name+" locale=\""+key + \
                "\">"+get_cdata(obj[key])+"</"+name+">\n"
    result += "\t</"+names+">\n"
    return result


def add_version(value):
    return add_single("version", value)


def add_uiVersion(value):
    return add_single("uiVersion", value)


def add_author(value):
    return add_single("author", value)


def add_authorID(value):
    return add_single("add_authorID", value)


def add_designer(value):
    return add_single("designer", value)


def add_title(value):
    return add_single("title", value)


def add_description(value):
    return add_single("description", value)


def build_description(data):
    locales = data["locales"]
    result = ""
    result += (get_xml())
    result += ("<theme>\n")
    if(data["author"]):
        result += (add_single("author", data["author"]))
    if(data["authorID"]):
        result += (add_single("authorID", data["authorID"]))
    if(data["designer"]):
        result += (add_single("designer", data["designer"]))
    if(data["description"]):
        result += (add_single("description", data["description"]))
    if(data["title"]):
        result += (add_single("title", data["title"]))
    if(data["uiVersion"]):
        result += (add_single("uiVersion", data["uiVersion"]))
    if(data["version"]):
        result += (add_single("version", data["version"]))
    for key in locales:
        name = locales[key]
        value = name["value_name"]
        result += (add_multiple(key, value, name))
    result += ("</theme>\n")
    return result

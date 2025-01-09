# -*- coding: utf-8 -*-
"""
@author: Noemi E. Cazzaniga - 2024
@email: noemi.cazzaniga@polimi.it
"""


import requests
import xml.etree.ElementTree as ET
import json
import re
from pandas import DataFrame
from gzip import decompress
from itertools import product



__ra__ = {"timeout": 120.}
__agency_by_provider__ = [("EUROSTAT", "ESTAT"),
                          ("COMEXT", "ESTAT"),
                          ("COMP", "COMP"),
                          ("EMPL", "EMPL"),
                          ("GROW", "GROW"),
                          ]



class __Uri__():

    BASE_URL = {"EUROSTAT": "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/",
                "COMEXT": "https://ec.europa.eu/eurostat/api/comext/dissemination/sdmx/2.1/",
                "COMP": "https://webgate.ec.europa.eu/comp/redisstat/api/dissemination/sdmx/2.1/",
                "EMPL": "https://webgate.ec.europa.eu/empl/redisstat/api/dissemination/sdmx/2.1/",
                "GROW": "https://webgate.ec.europa.eu/grow/redisstat/api/dissemination/sdmx/2.1/",
               }
    BASE_ASYNC_URL = {"EUROSTAT": "https://ec.europa.eu/eurostat/api/dissemination/1.0/async/",
                      "COMEXT": "https://ec.europa.eu/eurostat/api/comext/dissemination/1.0/async/",
                      "COMP": "https://ec.europa.eu/eurostat/api/compl/dissemination/1.0/async/",
                      "EMPL": "https://ec.europa.eu/eurostat/api/empl/dissemination/1.0/async/",
                      "GROW": "https://ec.europa.eu/eurostat/api/grow/dissemination/1.0/async/",
                     }
    XMLSNS_M = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message}"
    XMLSNS_S = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure}"
    XMLSNS_C = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common}"
    XMLSNS_L = "{http://www.w3.org/XML/1998/namespace}lang"
    XMLSNS_ENV = "{http://schemas.xmlsoap.org/soap/envelope/}"
    XMLSNS_ASYNC_NS0 = "{http://estat.ec.europa.eu/disschain/soap/asynchronous}"
    XMLSNS_ASYNC_NS1 = "{http://estat.ec.europa.eu/disschain/asynchronous}"
    XMLSNS_SYNC_NS0 = "{http://estat.ec.europa.eu/disschain/soap/extraction}"

    par_path = \
        XMLSNS_M + "Structures/" +\
        XMLSNS_S + "Constraints/" +\
        XMLSNS_S + "ContentConstraint/" +\
        XMLSNS_S + "CubeRegion/" +\
        XMLSNS_C + "KeyValue"
    val_path = XMLSNS_C + "Value"
    dim_path = \
        XMLSNS_M + "Structures/" +\
        XMLSNS_S + "DataStructures/" +\
        XMLSNS_S + "DataStructure/" +\
        XMLSNS_S + "DataStructureComponents/" +\
        XMLSNS_S + "DimensionList/" +\
        XMLSNS_S + "Dimension"
    dsd_path = \
        XMLSNS_M + "Structures/" +\
        XMLSNS_S + "Dataflows/" +\
        XMLSNS_S + "Dataflow/" +\
        XMLSNS_S + "Structure/Ref"
    ref_path = \
        XMLSNS_S + "LocalRepresentation/" +\
        XMLSNS_S + "Enumeration/Ref"
    async_key_path = \
        XMLSNS_ENV + "Body/" +\
        XMLSNS_ASYNC_NS0 + "asyncResponse/" +\
        XMLSNS_ASYNC_NS1 + "status/" +\
        XMLSNS_ASYNC_NS1 + "key"
    async_status_path = \
        XMLSNS_ENV + "Body/" +\
        XMLSNS_ASYNC_NS0 + "asyncResponse/" +\
        XMLSNS_ASYNC_NS1 + "status/" +\
        XMLSNS_ASYNC_NS1 + "status"
    sync_key_path = \
        XMLSNS_ENV + "Body/" +\
        XMLSNS_SYNC_NS0 + "syncResponse/queued/id"
    sync_status_path = \
        XMLSNS_ENV + "Body/" +\
        XMLSNS_SYNC_NS0 + "syncResponse/queued/status"
    codelist_path =  \
        XMLSNS_M + "Structures/" +\
        XMLSNS_S + "Codelists/" +\
        XMLSNS_S + "Codelist"


def set_requests_args(**kwargs):
    """
    Allows to set some arguments for "requests":
    - timeout: how long to wait for the server before raising an error. (optional)
        Default: 120 sec.
    - proxies : dict with protocol, user and password. (optional)
        For the Eurostat API, only https proxy.
        Examples: {'https': 'http://myuser:mypass@123.45.67.89:1234'}
                  {'https': 'https://123.45.67.89:1234'}
        Default: None.
    - verify : for the serverâ€™s TLS certificate. (optional)
        Default: None.
    - cert : user-provided SSL certificate. (optional)
       Default: None.
    Return None.

    """
    opt = ["timeout", "proxies", "verify", "cert"]
    assert set(kwargs.keys()).issubset(opt), "Argument not allowed: " + \
        ", ".join(list(set(kwargs).difference(opt)))
    global __ra__
    for k in kwargs:
        __ra__[k] = kwargs[k]


def get_requests_args():
    """
    Get the current set arguments for "requests".
    Return a dict with arg names and their respective values.
    """

    return __ra__


def setproxy(proxyinfo):
    """
    Set the proxies.
    If a proxy is required: proxyinfo = {"https": [username, password, 'http://url:port']}.
    If authentication is not needed, set username and password = None.
    Return None.
    """

    assert len(proxyinfo) == 1, "Error in proxyinfo."
    assert type(proxyinfo) is dict, "Error: 'proxyinfo' must be a dictionary."
    assert "https" in proxyinfo.keys(), "The key 'https' is missing in proxyinfo."
    assert (":" in proxyinfo["https"][2] and
            "//" in proxyinfo["https"][2]), "Error in proxy host. It must be in the form: 'http://url:port'"
    global __ra__
    [protocol, url_port] = proxyinfo['https'][2].split('//')
    try:
        myhttpsquotedpass = requests.utils.quote(proxyinfo['https'][1])
        myhttpsproxy = proxyinfo['https'][0] + ':' + myhttpsquotedpass + '@' + url_port
    except:
        myhttpsproxy = url_port
    __ra__['proxies'] = {'https': protocol + '//' + myhttpsproxy}


def get_data(code, flags=False, **kwargs):
    """
    Download an Eurostat dataset (of given code).
    Return it as a list of tuples.
    """

    opt = ["filter_pars", "verbose", "reverse_time"]
    assert set(kwargs).issubset(opt), "Argument not allowed: " + \
        ", ".join(list(set(kwargs).difference(opt)))
    filter_pars = kwargs.get("filter_pars", dict())
    verbose = kwargs.get("verbose", False)
    reverse_time = kwargs.get("reverse_time", False)
    assert type(code) is str, "Error: 'code' must be a string."
    assert type(flags) is bool, "Error: 'flags' must be a boolean."
    assert type(filter_pars) is dict, "Error: 'filter_pars' must be a dictionary."
    assert type(verbose) is bool, "Error: 'verbose' must be a boolean."
    assert type(reverse_time) is bool, "Error: 'reverse_time' must be a boolean."
    __, provider, dims = __get_dims_info__(code, detail='order')

    if filter_pars == dict():
        filt = "?"
    else:
        start = ""
        end = ""
        nontime_pars = {}
        for k in filter_pars:
            if k == "startPeriod":
                fs = str(filter_pars[k])
                start = "startPeriod=" + fs + "&"
            elif k == "endPeriod":
                fe = str(filter_pars[k])
                end = "endPeriod=" + fe + "&"
            else:
                nontime_pars[k] = filter_pars[k] if type(
                    filter_pars[k]) is list else [filter_pars[k], ]
        
        if len(nontime_pars) > 0:
            filter_lists = [tuple(zip(
                (d,) * len(nontime_pars[str(d)]), nontime_pars[str(d)])) for d in nontime_pars]
            cart = [el for el in product(*filter_lists)]
            filter_str_list = [
                ".".join([dict(c).get(j[1], "") for j in sorted(dims)]) for c in cart]
            filt = []
            for f in filter_str_list:
                filt.append("/" + f + "?" + start + end)
        else:
            filt = ["?" + start + end, ]

    alldata = []
    is_header = False
    if flags:
        n_el = 2
    else:
        n_el = 1
    filt_len = len(filt)
    if verbose:
        counter = 0
        print("\rDownload progress: {:3.1%}".format(counter), end="\r")
    for f_str in filt:
        data_url = __Uri__.BASE_URL[provider] +\
                    "data/" +\
                    code +\
                    f_str +\
                    "format=TSV&compressed=true"
        resp = __get_resp__(data_url, provider=provider)
        data = []
        if resp is not None:
            try:
                dec = decompress(resp.content).decode("utf-8")
            except:
                print(resp.content)
            n_text_fields = len(dec[:dec.find("\t")].split(","))
            raw_data = dec.split("\r\n")
            is_first_data_row = True
            for row in raw_data:
                row_list = re.split(r"\t|,", row)
                if is_first_data_row:
                    is_first_data_row = False
                    if not is_header:
                        is_header = True
                        if flags:
                            head = row_list[:n_text_fields] +\
                                      [x.strip()+f for x in row_list[n_text_fields:]
                                           for f in ("_value", "_flag")]
                        else:
                            head = [x.strip() for x in row_list]
                        alldata = [tuple(head),]
                elif row_list != ['',]:
                    l = row_list[:n_text_fields]
                    for el in row_list[n_text_fields:]:
                        tmp = [t.strip() for t in el.split(" ")]
                        if tmp[0] == None:
                            tmp = [None, None]
                        elif tmp[0] == ":" or tmp[0] == "0n" or tmp[0] == "n":
                            if len(tmp) == 1:
                                tmp.insert(0, None)
                            elif len(tmp) == 2:
                                tmp[1] = " ".join(tmp).strip()
                                tmp[0] = None
                            else:
                                raise Exception
                        else:
                            try:
                                tmp[0] = float(tmp[0])
                            except:
                                tmp = [el, None]
                        l.extend(tmp[:n_el])
                    data.append(tuple(l))           

        alldata.extend(data)

        if verbose:
            counter += 1
            print("\rDownload progress: {:3.1%}".format(
                counter/filt_len), end="\r")

    if verbose:
        print("\n")

    if reverse_time:
        if flags:
            for en1, a in enumerate(alldata):
                valflags = list(a[n_text_fields:])
                valflags.reverse()
                for en2, v in enumerate(valflags):
                    if en2 % 2 == 0:
                        fl = v
                    else:
                        valflags[en2 - 1] = v
                        valflags[en2] = fl
                alldata[en1] = a[:n_text_fields] + tuple(valflags)
        else:
            for en, a in enumerate(alldata):
                alldata[en] = a[:n_text_fields] + \
                                tuple([val for val in list(a[n_text_fields:]).__reversed__()])

    if alldata != []:
        return alldata
    else:
        return None


def get_data_df(code, flags=False, **kwargs):
    """
    Download an Eurostat dataset (of given code).
    Return it as a Pandas dataframe.
    """

    d = get_data(code, flags, **kwargs)

    if d != None:
        return DataFrame(d[1:], columns=d[0])
    else:
        return


def get_pars(code):
    """
    Download the pars to filter the Eurostat dataset with given code.
    Return a list.
    """
    assert type(code) is str, "Error: 'code' must be a string."
    
    __, __, dims = __get_dims_info__(code, detail='name')
    return dims


def get_dic(code, par=None, **kwargs):
    """
    Download an Eurostat codelist with the descriptions
    of the dimensions of a dataset or
    of the parameter values.
    Return it as a Python list, a dataframe or a dictionary.
    """

    kwargs_opt = ["frmt", "full", "lang"]
    frmt_opt = ["list", "dict", "df"]
    lang_opt = ["en", "fr", "de"]
    assert set(kwargs).issubset(kwargs_opt), "Argument not allowed: " + \
        ", ".join(list(set(kwargs).difference(kwargs_opt)))
    frmt = kwargs.get("frmt", "list")
    full = kwargs.get("full", True)
    lang = kwargs.get("lang", "en")
    assert type(code) is str, "Error: 'code' must be a string."
    assert type(par) is str or par is None, "Error: 'par' must be a string."
    assert frmt in frmt_opt, "Error: 'frmt' must be " + " or ".join(frmt_opt)
    assert type(full) is bool, "Error: 'full' must be a boolean."
    assert lang in lang_opt, "Error: 'lang' must be " + " or ".join(lang_opt)
    
    if par:    
        agencyId, provider, dims = __get_dims_info__(code, detail='basic')
        try:
            par_id = [d[1] for d in dims if d[0].lower() == par.lower()][0]
        except:
            print('Error: ' + par + ' not in ' + code)
            raise
        url = __Uri__.BASE_URL[provider] + "codelist/" + agencyId + \
            "/"+ par_id + "/latest?format=TSV&compressed=true&lang=" + lang
        resp = __get_resp__(url)
        resp_list = decompress(resp.content).decode("utf-8").split("\r\n")
        resp_list.pop()
        tmp_list = [tuple(el.split("\t")) for el in resp_list]
        if full:
            l = tmp_list
        else:
            par_values = get_par_values(code, par)
            l = [el for el in tmp_list if el[0] in par_values]
        columns = ['val', 'descr']
    else:
        __, __, l = __get_dims_info__(code, detail='descr', lang=lang)
        columns = ['dim', 'name', 'descr']
    
    if frmt == "list":
        return l
    elif frmt == "dict":
        if par:
            return dict(l)
        else:
            return dict([(ld[0], {'name': ld[1], 'descr': ld[2]}) for ld in l])
    elif frmt == 'df':
        return DataFrame(l, columns=columns)


def get_par_values(code, par):
    """
    Download an Eurostat codelist for a given parameter of a given dataset.
    Return it as a list.
    """
    assert type(code) is str, "Error: 'code' must be a string."
    assert type(par) is str, "Error: 'par' must be a string."
    
    agencyId, provider, __ = __get_dims_info__(code, detail='empty')
    url = __Uri__.BASE_URL[provider] +\
            "contentconstraint/" +\
            agencyId +\
            "/" +\
            code
    resp = __get_resp__(url)
    root = __get_xml_root__(resp)
    return [v.text for p in root.findall(__Uri__.par_path) if p.get("id").lower() == par.lower() for v in p.findall(__Uri__.val_path)]


def get_toc(**kwargs):
    """
    Download the Eurostat table of contents of all the datasets, or
    of only one if the argument dataset is not 'all'.
    agency can be: 'EUROSTAT', 'COMEXT', 'COMP', 'EMPL', 'GROW' (even in a list) or 'all'.
    lang can be 'en'', 'fr', 'de'.
    Return it as a list of tuples.
    """
    kwargs_opt = ['agency', 'dataset', 'lang']
    assert set(kwargs.keys()).issubset(kwargs_opt), "Argument not allowed: " + \
        ", ".join(list(set(kwargs).difference(kwargs_opt)))
    agency = kwargs.get('agency', 'all')
    dataset = kwargs.get('dataset', 'all')
    lang = kwargs.get('lang', 'en')
    done = False
    
    toc = [("title",
            "code",
            "type",
            "last update of data",
            "last table structure change",
            "data start",
            "data end",
            # "agencyId"
            ), ]

    if agency == 'all':
        agency = list(__Uri__.BASE_URL.keys())
    else:
        assert (type(agency) == str or type(agency) == list), 'Agency must be a string or a list.'
        if type(agency) == str:
            agency = [agency,]
            
    for prov in agency:
        base_url = __Uri__.BASE_URL[prov]
        if dataset == 'all':
            url = base_url +\
                    "dataflow/all?format=JSON&compressed=true&lang=" +\
                    lang
        else:
            url = base_url +\
                    "dataflow/" +\
                    dict(__agency_by_provider__)[prov] +\
                    "/" +\
                    dataset +\
                    "?format=JSON&compressed=true&lang=" +\
                    lang
        resp = __get_resp__(url)
        if resp.ok:
            resp_txt = decompress(resp.content).decode("utf-8")
            resp_dict = json.loads(resp_txt)
            if dataset == 'all':
                content = resp_dict["link"]["item"]
            else:
                content = [resp_dict,]
                done = True
            for el in content:
                title = el["label"]
                code = el["extension"]["id"]
                _type = el["class"]
                data_start = None
                data_end = None
                for a in el["extension"]["annotation"]:
                    if a["type"] == "UPDATE_DATA":
                        last_update = a["date"]
                    elif a["type"] == "UPDATE_STRUCTURE":
                        last_struct_change = a["date"]
                    elif a["type"] == "OBS_PERIOD_OVERALL_OLDEST":
                        data_start = a["title"]
                    elif a["type"] == "OBS_PERIOD_OVERALL_LATEST":
                        data_end = a["title"]
                # agencyId = el["extension"]["agencyId"]
                toc.append((title,
                            code,
                            _type,
                            last_update,
                            last_struct_change,
                            data_start,
                            data_end,
                            # agencyId
                            ))
            if done:
                break
    return toc


def get_toc_df(**kwargs):
    """
    Download the Eurostat table of contents of all the datasets, or
    of only one if the argument dataset is not 'all'.
    agency can be: 'EUROSTAT', 'COMEXT', 'COMP', 'EMPL', 'GROW' (even in a list) or 'all'.
    lang can be 'en'', 'fr', 'de'.
    """

    t = get_toc(**kwargs)

    return DataFrame(t[1:], columns=t[0])


def subset_toc_df(toc_df, keyword):
    """
    Extract from the Eurostat table of contents where the title contains a given keyword.
    Return a pandas dataframe.
    """
    assert type(keyword) is str, "Error: 'keyword' must be a string."

    return toc_df[toc_df["title"].str.contains(keyword, case=False)]


def __get_dims_info__(code, **kwargs):
    """
    if detail == 'descr' : dims = [(codelist_name, full_name, description), ...]
    if detail == 'order' : dims = [(position, codelist_name), ...]
    if detail == 'name' : dims = [codelist_name, ...]
    if detail == 'empty' : dims = []
    if detail == 'basic' :  dims = [(codelist_name, dimension_ID), ...]
    """

    assert set(kwargs.keys()), 'Wrong kwargs'
    detail = kwargs.get('detail', None)
    lang = kwargs.get('lang', 'en')
    
    # retrieve agencyId, provider, df_root, dsd_root
    found = False
    i = 0
    df_tail = "/latest?detail=referencepartial&references=descendants" if detail == 'descr' else \
                "/latest"
    while (not found) and (i <= len(__agency_by_provider__)):
        try:
            df_url = __Uri__.BASE_URL[__agency_by_provider__[i][0]] +\
                    "dataflow/" +\
                    __agency_by_provider__[i][1] +\
                    "/" +\
                    code +\
                    df_tail
            resp = __get_resp__(df_url, is_raise=False)
            df_root = __get_xml_root__(resp)
            agencyId = __agency_by_provider__[i][1]
            provider = __agency_by_provider__[i][0]
            if detail == 'empty':
                return [agencyId, provider, []]
            found = True
        except:
            pass
        i += 1
    if not found:
        print("Dataset not found: " + code)
        raise ValueError
    else:
        dsd_code = df_root.find(__Uri__.dsd_path).get("id")
    dsd_url = __Uri__.BASE_URL[provider] +\
                "datastructure/" +\
                agencyId +\
                "/" +\
                dsd_code +\
                "/latest"
    resp = __get_resp__(dsd_url)
    dsd_root = __get_xml_root__(resp)
    
    # get dims
    if detail == 'name':
        dims = [dim.get("id")
                 for dim in dsd_root.findall(__Uri__.dim_path)]
    elif detail == 'basic':
        dims = [(dim.get("id"), dim.find(__Uri__.ref_path).get("id"))
                 for dim in dsd_root.findall(__Uri__.dim_path)]
    elif detail == 'order':
        dims = [(dim.get("position"), dim.get("id"))
                 for dim in dsd_root.findall(__Uri__.dim_path)]
    elif detail == 'descr':
        descr = df_root.findall(__Uri__.codelist_path)
        dims = []
        for dim1 in dsd_root.findall(__Uri__.dim_path):
            dimension_ID = dim1.find(__Uri__.ref_path).get("id")
            for dim in descr:
                if dim.get("id") == dimension_ID:
                    full_name = None
                    for d in dim.findall(__Uri__.XMLSNS_C + 'Name'):
                        if d.get(__Uri__.XMLSNS_L, None) == lang:
                            full_name = d.text
                    if full_name == None:
                        full_name = dim.findtext(__Uri__.XMLSNS_C + 'Name')
                    description = dim.findtext(__Uri__.XMLSNS_C + 'Description')
                    break
            dims.append((dim1.get("id"),
                         full_name,
                         description))

    return [agencyId, provider, dims]


def __get_xml_root__(resp):
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        raise e
    return root


def __get_raw_resp__(url, is_raise):
    is_ok = False
    max_att = 4
    n_att = 0
    # print(url)
    while (not is_ok) and (n_att != max_att):
        n_att += 1
        try:
            resp = requests.get(url,  **__ra__)
            is_ok = resp.ok
        except Exception as e:
            last_exception = e
    if "resp" not in locals():
        if is_raise:
            raise last_exception
        else:
            resp = None
    elif resp.url == "https://sorry.ec.europa.eu/":
        print("Server inaccessibility\n")
        print("The server is temporarily unavailable\n")
        raise ConnectionError(url)
    return resp


def __get_resp__(url,**kwargs):
    assert set(kwargs.keys()).issubset(['provider', 'is_raise'])
    is_raise = kwargs.get("is_raise", True)
    resp = __get_raw_resp__(url, is_raise)
    if resp is not None:
        if b"<S:Fault" in resp.content:
            if resp.ok:
                resp = None
            else:
                if is_raise:
                    root = __get_xml_root__(resp)
                    for el in list(root):
                        print(": ".join([el.tag, el.text]))
                    resp.raise_for_status()
                else:
                    resp = None
        elif b"status></" in resp.content:
            root = __get_xml_root__(resp)
            try:
                status = root.find(__Uri__.async_status_path).text
            except:
                try:
                    status = root.find(__Uri__.sync_status_path).text
                except:
                    print('Unexpected error: Status path not found.')
                    raise ConnectionError
            try:
                key = root.find(__Uri__.async_key_path).text
            except:
                try:
                    key = root.find(__Uri__.sync_key_path).text
                except:
                    print('Unexpected error: Key path not found.')
                    raise ConnectionError
            async_status_url = __Uri__.BASE_ASYNC_URL[kwargs["provider"]] +\
                                "status/" +\
                                key
            while status != "AVAILABLE":
                resp = __get_raw_resp__(async_status_url, True)
                root = __get_xml_root__(resp)
                status = root.find(__Uri__.async_status_path).text
                if status in ["EXPIRED", "UNKNOWN_REQUEST"]:
                    raise ConnectionError
                elif status not in ["SUBMITTED", "PROCESSING", "AVAILABLE"]:
                    print("Unexpected async status: " + status + " Try again.")
                    raise ConnectionError
            resp = __get_resp__(async_status_url.replace("/status/","/data/"))
    return resp
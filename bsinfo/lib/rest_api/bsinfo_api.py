import re
from flask_restplus import Api, Resource, Namespace, fields
from flask import request
from lib.bsmysql import BsMySQL, get_cached_debug_cookie
from lib.bi_util import get_json_with_socdem, load_const_update, get_frontend_for_dsp
from yabs_filter_record import decode as yabs_url_decrypt
import library.python.resource as res
from urllib import unquote
from lib.common_request_class import CommonRequest
from font_info import compute_prod_text_pixel_width


bsinfo_ns = Namespace('bsinfo-restapi/v1.0', description='BSINFO Rest Api v 1.0')

model_decrypt_url = bsinfo_ns.model('DecryptURL result', {
    'crypted_url': fields.String(required=True, description='BS Url for decrypt'),
    'decrypted_url': fields.String(required=False, description='Decrypted URL')
})

model_debug_cookie = bsinfo_ns.model('DebugCookie result', {
    'debug_cookie': fields.String(required=False, description='BS debug cookie')
})

output_model_calc_width = bsinfo_ns.model('Calc pixel width calculated result', {
    'pixel_width': fields.Integer(description="Calculated pixel width")
})

input_model_calc_width = bsinfo_ns.model('Calc pixel width param', {
    'font_name': fields.String(enum=['arial', 'arialbold', 'dejavusansmono'], required=True, description='Font name'),
    'font_size': fields.Integer(min=1, required=True, description='Font Size'),
    'delta_px': fields.Integer(min=1, required=True, description='Delta px'),
    'space_px': fields.Integer(min=1, required=True, description='Space px'),
    'text': fields.String(required=True, description='Text for calculaion')
})

output_classic_request = bsinfo_ns.model('Make Classic Request output', {
    'bs_request_type': fields.String(required=True, description='Request name'),
    'req_host': fields.String(required=True, default="default", description='Host used for request'),
    'req_code': fields.String(required=True, description="Response HTTP code"),
    'req_method': fields.String(required=True, description="Used request HTTP method[GET|PUT]"),
    'req_url': fields.String(required=True, description="URL used for request"),
    'curl_command': fields.String(required=True, description="Curl command for repeat request with same params"),
    'sysconst_update': fields.String(required=True, description='BS debug sysconst-update'),
    'yabs_debug_options': fields.String(required=True, description='BS debug options'),
    'element_post': fields.String(required=True, description='Additional request args'),
    'jquery_json_size_hr': fields.String(required=False, description="Jquery json view human readable size"),
    'jquery_json_size': fields.Integer(required=False, description="Jquery json view size"),
    'jquery_json': fields.String(required=False, description="Json for jquery view"),
    'req_post_body': fields.String(required=False, description="HTTP Request Post Body"),
    'resp_body': fields.String(required=False, description="HTTP Response Body"),
    'resp_body_size': fields.Integer(required=False, description="HTTP Response Body size"),
    'resp_body_size_hr': fields.String(required=True, description="Human readable response body size"),
    'body_search_string': fields.String(required=False, description="Search string in response body"),
    'body_founded_json_count': fields.String(required=False, description="Founded search string count in the body"),
    'body_founded_json_jquery_size': fields.String(required=False, description="Founded search size in json format"),
    'body_founded_json_jquery': fields.String(required=False, description="Founded search result in json format"),
    'error': fields.String(required=False, description="Error in request")
})

input_classic_request = bsinfo_ns.model('Make Classic Request input', {
    'bs_request_type': fields.String(enum=['RequestMeta', 'RequestSearch', 'RequestDSP', 'RequestRank', 'RequestPartner', 'RequestSSPGet', 'RequestAudit',
                                           'RequestBansearch', 'RequestCount', 'RequestCountPartner', 'RequestRtbcount'],
                                     default="RequestSearch", required=True, description='Request name'),
    'yandexuid': fields.String(required=False, default=["1"], description='yandexuid for request'),
    'yabs_debug_options': fields.String(required=False, description='BS debug options'),
    'user_agent': fields.String(required=False, default="MSIE", description='User-agent'),
    'sysconst_update': fields.String(required=False, default="", description='BS sysconst update'),
    'element_post': fields.String(required=True, description='Additional request args and values, may be empty'),
    'make_json_form': fields.Boolean(required=False, default=False, description='View json response'),
    'make_jquery_json': fields.Boolean(required=False, default=False, description='Make view jquery json'),
    'get_args': fields.String(required=False, default="", description='Additional query args URL'),
    'bs_post_data': fields.String(required=False, default="", description='DSP request post json'),
    'bs_host': fields.String(required=False, default="default", description='Host to request'),
    'body_search_string': fields.String(required=False, default="", description='String to search in Response'),
    'search_include_subjson': fields.Boolean(required=False, default="", description='Include sub-json in search result Response'),
    'app_host': fields.String(required=False, default="", description='Debug app host'),
    'user_request_name': fields.String(required=False, default="", description='Request name to save in request history'),
    'debug_page': fields.String(required=False, default="", description='Not empty if use debug page test_rest_request.html')
})

model_get_referer = bsinfo_ns.model('Get refererr by Page Id', {
    'referer': fields.String(required=False, description='referer')
})

model_get_bigb_profile = bsinfo_ns.model('Get socdem bigb profile by yandexuid', {
    'bigb_profile': fields.String(required=False, description='bigb profile')
})

bsinfo_api = Api(doc='/rest_console.htm', version='v1.0', title='BSINFO REST API Docs and Test',
                        description='BSINFO REST API', base_url='/test', contact_email="semenoviv@yandex-team.ru",
                        default='bsinfo-api', default_label='BSINFO REST API')

bsinfo_api.namespaces.pop(0)
bsinfo_api.add_namespace(bsinfo_ns)


def fillDebugPageField(data_req):
    # BEGIN STUB on empty field for Swagger or HTML POST form!!!
    # "string" val to empty ""
        for el in data_req.copy():
            if data_req[el] == "string":
                print "REST delete swagger string " + el
                data_req[el] = ""

        if data_req["bs_host"] == "":
            data_req["bs_host"] = "default"

        if data_req["yabs_debug_options"] == "":
            data_req[
                "yabs-debug-options"] = '{"logs": false, "mx": false, "mx_zero_features": false, "keywords": false, "business": false,' \
                                        ' "filter_log": false, "match_log": false, "force_event_log": false, "trace": false}'
        else:
            data_req["yabs-debug-options"] = data_req["yabs_debug_options"]

        request_type = data_req['bs_request_type']
        element_post = ""

        data_req['page_id'] = "49688"
        element_post += 'page_id' + ":" + data_req['page_id'] + ","

        if request_type == "RequestSearch" or request_type == "RequestCount" or request_type == "RequestCountPartner" or request_type == "RequestRtbcount":
            data_req['search_text'] = "toyota"
            element_post += "search_text" + ":" + data_req['search_text'] + ","
        elif request_type == "RequestRank":
            data_req['reg-id'] = "1"
            element_post += "reg-id" + ":" + data_req['reg-id'] + ","
        elif request_type == "RequestSSPGet" or request_type == "RequestAudit":
            data_req['page-ref'] = "http://auto.ru"
            element_post += 'page-ref' + ":" + data_req['page-ref'] + ","
            data_req['ssp-id'] = "1000"
            element_post += "ssp-id" + ":" + data_req['ssp-id'] + ","
        elif request_type == "RequestDSP":
            data_req['bs_post_data'] = res.find('/resource/request_dsp.json')
            if data_req["bs_host"] == "default":
                data_req["bs_host"] = get_frontend_for_dsp()

        data_req['element_post'] += element_post


@bsinfo_ns.route('/make_classic_request/')
@bsinfo_api.doc(id='Post json')
class MakeClassicRequest(Resource):
    @bsinfo_api.doc(id='Make Classic Request')
    @bsinfo_api.expect(input_classic_request, validate=True)
    @bsinfo_api.marshal_with(output_classic_request)
    def post(self):
        '''Make Classic Request'''
        data_req = request.get_json(silent=True)
        data_req['yandexuid_data'] = data_req['yandexuid']

        # fill field for debug page /test_rest_request.html
        if len(data_req["debug_page"]) > 0:
            fillDebugPageField(data_req=data_req)

        element_post = data_req['element_post']
        m = re.search('page_id:(\d+)', element_post)
        if m:
            page_id = str(m.group(1))
        else:
            page_id = None
        print "API page_id {}".format(page_id)
        if page_id is not None:
            referer = BsMySQL().get_ref_by_page_id(page_id)
            element_post += 'target-ref' + ":" + referer + ","
            element_post += 'page-ref' + ":" + referer + ","

        data_req['element_post'] = element_post
        cr = CommonRequest(data_req)
        cr.makeClassicRequest()
        rest_data_json = cr.getRequestRestApiData()

        return rest_data_json


class DecryptURL(object):
    def __init__(self, url):
        self.crypted_url = unquote(url)
        self.decrypted_url = yabs_url_decrypt(self.crypted_url)


@bsinfo_ns.route('/decrypt_yabs_url/<path:url>/')
@bsinfo_ns.doc(params={'url': 'BS url for decrypt'})
@bsinfo_api.response(200, 'Successful')
class DecryptURL_route(Resource):
    @bsinfo_api.marshal_with(model_decrypt_url)
    @bsinfo_api.doc(id='Decrypt BS URL')
    def get(self, url):
        '''Decrypt BS URL'''
        return DecryptURL(url)


class DebugCookie(object):
    def __init__(self):
        self.debug_cookie = get_cached_debug_cookie()


@bsinfo_ns.route('/get_debug_cookie/')
@bsinfo_api.response(200, 'Successful')
class DebugCookie_route(Resource):
    @bsinfo_api.marshal_list_with(model_debug_cookie)
    @bsinfo_api.doc(id='Get BS debug cookie')
    def get(self):
        '''Get BS debug cookie'''
        return DebugCookie()


@bsinfo_ns.route('/calc_pixel_width/')
@bsinfo_api.doc(id='Post json')
class CalcTextPixelWidth(Resource):
    @bsinfo_api.doc(id='Text pixel width calculation')
    @bsinfo_api.expect(input_model_calc_width, validate=True)
    @bsinfo_api.marshal_with(output_model_calc_width)
    def post(self):
        '''Text pixel width calculation'''
        data = request.get_json(silent=True)
        font_name = data['font_name']
        font_size = data['font_size']
        delta_px = data['delta_px']
        space_px = data['space_px']
        text = data['text'].encode('utf-8')
        pixel_width = compute_prod_text_pixel_width(font_name, font_size, delta_px, space_px, text)
        return {'pixel_width': pixel_width}


@bsinfo_ns.route('/get_referer_by_page_id/<string:page_id>/')
@bsinfo_ns.doc(params={'page_id': 'Page ID'})
@bsinfo_api.response(200, 'Successful')
class GetRefererByPageID(Resource):
    @bsinfo_api.marshal_with(model_get_referer)
    @bsinfo_api.doc(id='Get referer by Page ID')
    def get(self, page_id):
        '''Get referer by Page ID'''
        referer = BsMySQL().get_ref_by_page_id(page_id)
        return {'referer': referer}


@bsinfo_ns.route('/get_syconst_update/')
@bsinfo_api.response(200, 'Successful')
class GetSysconstUpdate(Resource):
    @bsinfo_api.doc(id='Get {"sysconst_update": sysconst update json}')
    def get(self):
        '''Get sysconst-update'''
        sysconst_update = load_const_update()
        return {'sysconst_update': sysconst_update}


@bsinfo_ns.route('/get_bigb_profile/<string:yandexuid>/')
@bsinfo_ns.doc(params={'yandexuid': 'user yandexuid'})
@bsinfo_api.response(200, 'Successful')
class GetBigbProfle(Resource):
    # @bsinfo_api.marshal_with(model_get_bigb_profile)
    @bsinfo_api.doc(id='Get {"bigb_profile": bigb profile json}')
    def get(self, yandexuid):
        '''Get bigb profile'''
        if (yandexuid is not None and len(yandexuid) > 0):
            try:
                sd_prof = get_json_with_socdem({}, yandexuid)
                sd_prof = sd_prof['user']
            except:
                sd_prof = {}
        else:
            sd_prof = {}
        return {'bigb_profile': sd_prof}

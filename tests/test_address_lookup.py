import ast
import io
import json
import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch
from flask import Flask, request, jsonify

class AddressLookup(unittest.TestCase):
    def setUp(self):
        self.app=Flask(__name__)
        tree=ast.parse((Path(__file__).resolve().parents[1]/'app.py').read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='address_lookup')
        node.decorator_list=[]
        self.ns=dict(os=os,re=re,json=json,request=request,jsonify=jsonify,get_settings=lambda:{'address_lookup_api_key':'test'})
        exec(compile(ast.Module(body=[node],type_ignores=[]),'lookup','exec'),self.ns)
    def call(self,postcode):
        with self.app.test_request_context('/api/address-lookup',query_string={'postcode':postcode}):
            return self.ns['address_lookup']()
    def test_invalid_and_missing_setup(self):
        self.assertEqual(self.call('bad')[1],400)
        self.ns['get_settings']=lambda:{}
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(self.call('SW1A 2AA')[1],503)
    def test_full_address_mapping(self):
        payload={'code':2000,'result':[{'line_1':'10 Example Street','line_2':'Example Estate','line_3':'District','post_town':'LONDON','postcode':'SW1A 2AA'}]}
        with patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(payload).encode())) as fetch:
            response=self.call('sw1a 2aa')
            address=response.get_json()['addresses'][0]
            self.assertEqual(address['address2'],'Example Estate, District')
            self.assertEqual(address['country'],'United Kingdom')
            self.assertNotIn('test',fetch.call_args.args[0].full_url)
    def test_outage(self):
        with patch('urllib.request.urlopen',side_effect=OSError('unavailable')):
            self.assertEqual(self.call('SW1A 2AA')[1],502)

if __name__=='__main__':unittest.main()

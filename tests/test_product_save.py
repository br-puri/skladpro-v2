"""Exercise product form saves without connecting to the database."""
import ast
from pathlib import Path
import unittest
from unittest.mock import Mock
from flask import Flask, render_template, request, flash

class ProductSave(unittest.TestCase):
    def test_blank_numeric_fields_and_failed_upload(self):
        root=Path(__file__).resolve().parents[1]
        app=Flask(__name__,template_folder=str(root/'templates'));app.secret_key='test'
        nodes=[]
        for node in ast.parse((root/'app.py').read_text()).body:
            if isinstance(node,ast.FunctionDef) and node.name in {'_product_fields','add_product'}:
                node.decorator_list=[];nodes.append(node)
        db=Mock();db.__enter__=Mock(return_value=db);db.__exit__=Mock(return_value=False)
        db.execute.return_value.fetchall.return_value=[]
        ns=dict(request=request,app=app,flash=flash,render_template=render_template,get_db=lambda:db,
                _save_photo=Mock(side_effect=RuntimeError('Upload unavailable')))
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'app.py','exec'),ns)
        app.add_url_rule('/products/add', 'add_product', ns['add_product'], methods=['POST'])
        app.logger.disabled=True
        app.jinja_env.globals.update(url_for=lambda *a,**k:'/',get_flashed_messages=lambda **k:[],photo_url=lambda p:p)
        values={'name':'Example','cost':'','price':'','min_stock':'','cbm':'0.12'}
        with app.test_request_context('/products/add',method='POST',data=values):
            fields=ns['_product_fields'](request.form)
            self.assertEqual(fields[6:9],(0,0,0))
            html,status=ns['add_product']()
            self.assertEqual(status,422)
            self.assertIn('Example',html)
            self.assertIn('0.120000',html)
        self.assertFalse(any('INSERT' in str(c) for c in db.execute.call_args_list))

if __name__=='__main__': unittest.main()

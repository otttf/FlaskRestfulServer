from flask import Flask, request, current_app, Response
from werkzeug.exceptions import HTTPException
import json

__all__ = ('app',)

app = Flask(__name__)
app.config.BOUNDARY_LINE_WIDTH = 100


def boundary(header: str):
    """分界线"""
    return f' {header} '.center(app.config.BOUNDARY_LINE_WIDTH, '=')


def stringify(bs: bytes):
    try:
        return bs.decode()
    except UnicodeDecodeError:
        return '(bytes)'


def format_json(bs: bytes):
    try:
        return json.dumps(json.loads(request.data), ensure_ascii=False, indent=4)
    except (TypeError, json.JSONDecodeError):
        return stringify(bs)


# TODO 实现对request.args等的hook，记录字段的使用情况，如果没使用或者不完全使用则在Response的Header中返回警告

@app.before_request
def log_request_info():
    """输出HTTP Request"""
    full_path = request.full_path if len(request.query_string) else request.path
    protocol = request.environ['SERVER_PROTOCOL']
    body = ''
    if request.headers.get('Content-Length', 0, int) != 0:
        if len(request.files) > 0 or len(request.form) > 0:
            body += '(form-data-params)\n'
            for k, v in request.form.items(True):
                body += f'{k}: {v}\n'
            body += '(form-data-files)\n'
            for k, v in request.files.items(True):
                body += f'{k}: {v}\n'
            body = body[:-1]
        elif request.headers.get('Content-Type') == 'application/json':
            body = format_json(request.data)
        else:
            body = stringify(request.data)
    request_info = (f"\n{boundary('Begin Request')}\n"
                    f"{request.method} {full_path} {protocol}\n"
                    f'{request.headers}'
                    f'{body}\n'
                    f"{boundary('End Request')}")
    current_app.logger.info(request_info)


@app.after_request
def log_response_info(response: Response):
    """输出HTTP Response"""
    if response.headers.get('Content-Type') == 'application/octet-stream' or response.headers.get(
            'Content-Disposition'):
        body = '(file bytes)'
    elif request.headers.get('Content-Type') == 'application/json':
        body = format_json(request.data)
    else:
        body = stringify(request.data)
    response_info = (f"\n{boundary('Begin Response')}\n"
                     f'{response.headers}'
                     f'{body}\n'
                     f"{boundary('End Response')}")
    current_app.logger.info(response_info)
    return response


@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        response = e.get_response()
        # 将body用Json格式错误代替
        response.data = json.dumps({
            "code": e.code,
            "name": e.name,
            "description": e.description
        })
        response.content_type = "application/json"
        return response
    else:
        current_app.logger.debug('未处理错误')
        return e.get_response()

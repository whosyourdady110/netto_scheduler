import socket
import json


class ServiceDescApi:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.service_name = "$serviceDesc"

    def get_server_desc(self):
        res_str = self.invoke_method('getServerDesc', None)
        res_dict = json.loads(res_str)
        if res_dict['success']:
            return res_dict['retObject']
        else:
            raise Exception(res_dict['errorMessage'])

    def find_services(self):
        res_str = self.invoke_method('findServices', None)
        res_dict = json.loads(res_str)
        if res_dict['success']:
            return res_dict['retObject']
        else:
            raise Exception(res_dict['errorMessage'])

    def ping_service(self, data):
        res_str = self.invoke_method('pingService', [data])
        res_dict = json.loads(res_str)
        if res_dict['success']:
            return res_dict['retObject']
        else:
            raise Exception(res_dict['errorMessage'])

    def invoke_method(self, method, args):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((self.server_ip, self.server_port))
            if args is not None:
                body = json.dumps(args)
            else:
                body = '[]'
            body_bytes = bytes(body, encoding='utf-8')
            header_content_bytes = bytes("service:" + self.service_name + "\r\nmethod:" + method, encoding='utf-8')
            header = "NETTO::2/" + str(len(header_content_bytes)) + "/" + str(len(body_bytes))
            header = header.ljust(64)
            header_bytes = bytes(header, encoding='utf-8')
            sock.send(header_bytes + header_content_bytes + body_bytes)
            total_data = []
            data = ''
            end_str = b'\r\n'
            while True:
                data = sock.recv(1024)
                if end_str in data:
                    total_data.append(data[:data.find(end_str)])
                    break
                total_data.append(data)
                if len(total_data) > 1:
                    # check if end_of_data was split
                    last_pair = total_data[-2] + total_data[-1]
                    if end_str in last_pair:
                        total_data[-2] = last_pair[:last_pair.find(end_str)]
                        total_data.pop()
                        break
            res_bytes = b''.join(total_data)
            return res_bytes.decode("utf-8")
        finally:
            sock.close()


if __name__ == '__main__':
    desc_obj = ServiceDescApi('192.168.2.38', 9229)
    res = desc_obj.get_server_desc()
    print('app:' + res['serviceApp'] + ",group:" + res['serviceGroup'])

    res = desc_obj.find_services()
    for service_desc in res:
        print('app:' + service_desc['serviceApp'] + ",name:" + service_desc['serviceName'] + ",timeout：" + str(service_desc[
            'timeout']) + ",interface:" + service_desc['interfaceClazz'])

    res = desc_obj.ping_service("abc")
    print(str(res))

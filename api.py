# ارتباط با API پنل 3X-UI

import aiohttp
import json
import uuid
import time
from typing import Optional
from config import PANEL_URL, PANEL_USERNAME, PANEL_PASSWORD


class Panel3XUI:
    def __init__(self):
        self.base_url = PANEL_URL
        self.username = PANEL_USERNAME
        self.password = PANEL_PASSWORD
        self.session: Optional[aiohttp.ClientSession] = None
        self.cookies = None
    
    async def __aenter__(self):
        await self.create_session()
        await self.login()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_session()
    
    async def create_session(self):
        """ایجاد session جدید"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(ssl=False)
            self.session = aiohttp.ClientSession(connector=connector)
    
    async def close_session(self):
        """بستن session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def login(self) -> bool:
        """ورود به پنل و دریافت کوکی"""
        try:
            url = f"{self.base_url}/login"
            data = {
                "username": self.username,
                "password": self.password
            }
            
            async with self.session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        self.cookies = response.cookies
                        return True
                return False
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    async def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """ارسال درخواست به API"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == "GET":
                async with self.session.get(url, cookies=self.cookies) as response:
                    return await response.json()
            elif method.upper() == "POST":
                async with self.session.post(url, json=data, cookies=self.cookies) as response:
                    return await response.json()
            else:
                return {"success": False, "msg": "Invalid method"}
        except Exception as e:
            print(f"Request error: {e}")
            return {"success": False, "msg": str(e)}
    
    # ==================== Inbound Operations ====================
    
    async def get_inbounds(self) -> list:
        """دریافت لیست inboundها"""
        result = await self._request("GET", "/panel/api/inbounds/list")
        if result.get("success"):
            return result.get("obj", [])
        return []
    
    async def get_inbound(self, inbound_id: int) -> dict:
        """دریافت اطلاعات یک inbound"""
        result = await self._request("GET", f"/panel/api/inbounds/get/{inbound_id}")
        if result.get("success"):
            return result.get("obj", {})
        return {}
    
    # ==================== Client Operations ====================
    
    async def add_client(self, inbound_id: int, email: str, uuid_str: str = None,
                         total_gb: float = 0, expiry_time: int = 0,
                         limit_ip: int = 0, enable: bool = True) -> dict:
        """افزودن کلاینت جدید به inbound"""
        if uuid_str is None:
            uuid_str = str(uuid.uuid4())
        
        # تبدیل گیگابایت به بایت
        total_bytes = int(total_gb * 1024 * 1024 * 1024) if total_gb > 0 else 0
        
        # تبدیل زمان به میلی‌ثانیه
        expiry_ms = expiry_time * 1000 if expiry_time > 0 else 0
        
        client_data = {
            "id": uuid_str,
            "email": email,
            "limitIp": limit_ip,
            "totalGB": total_bytes,
            "expiryTime": expiry_ms,
            "enable": enable,
            "tgId": "",
            "subId": str(uuid.uuid4())[:8],
            "reset": 0
        }
        
        data = {
            "id": inbound_id,
            "settings": json.dumps({"clients": [client_data]})
        }
        
        result = await self._request("POST", "/panel/api/inbounds/addClient", data)
        
        if result.get("success"):
            return {
                "success": True,
                "uuid": uuid_str,
                "email": email,
                "msg": "Client added successfully"
            }
        return {
            "success": False,
            "msg": result.get("msg", "Failed to add client")
        }
    
    async def delete_client(self, inbound_id: int, uuid_str: str) -> dict:
        """حذف کلاینت از inbound"""
        result = await self._request(
            "POST", 
            f"/panel/api/inbounds/{inbound_id}/delClient/{uuid_str}",
            {}
        )
        return result
    
    async def update_client(self, inbound_id: int, uuid_str: str, email: str,
                           total_gb: float = None, expiry_time: int = None,
                           enable: bool = None, limit_ip: int = None) -> dict:
        """بروزرسانی کلاینت"""
        # ابتدا اطلاعات فعلی را دریافت کنیم
        inbound = await self.get_inbound(inbound_id)
        if not inbound:
            return {"success": False, "msg": "Inbound not found"}
        
        # پیدا کردن کلاینت فعلی
        settings = json.loads(inbound.get("settings", "{}"))
        clients = settings.get("clients", [])
        
        current_client = None
        for client in clients:
            if client.get("id") == uuid_str or client.get("email") == email:
                current_client = client
                break
        
        if not current_client:
            return {"success": False, "msg": "Client not found"}
        
        # بروزرسانی مقادیر
        if total_gb is not None:
            current_client["totalGB"] = int(total_gb * 1024 * 1024 * 1024)
        if expiry_time is not None:
            current_client["expiryTime"] = expiry_time * 1000
        if enable is not None:
            current_client["enable"] = enable
        if limit_ip is not None:
            current_client["limitIp"] = limit_ip
        
        data = {
            "id": inbound_id,
            "settings": json.dumps({"clients": [current_client]})
        }
        
        result = await self._request(
            "POST",
            f"/panel/api/inbounds/updateClient/{uuid_str}",
            data
        )
        return result
    
    async def get_client_traffic(self, email: str) -> dict:
        """دریافت ترافیک کلاینت"""
        result = await self._request(
            "GET",
            f"/panel/api/inbounds/getClientTraffics/{email}"
        )
        
        if result.get("success"):
            obj = result.get("obj", {})
            # تبدیل بایت به گیگابایت
            up = obj.get("up", 0)
            down = obj.get("down", 0)
            total = up + down
            
            return {
                "success": True,
                "email": email,
                "upload_gb": round(up / (1024**3), 3),
                "download_gb": round(down / (1024**3), 3),
                "total_gb": round(total / (1024**3), 3),
                "upload_bytes": up,
                "download_bytes": down,
                "total_bytes": total
            }
        return {
            "success": False,
            "email": email,
            "msg": result.get("msg", "Failed to get traffic")
        }
    
    async def get_all_clients_traffic(self, inbound_id: int = None) -> list:
        """دریافت ترافیک همه کلاینت‌ها"""
        clients_traffic = []
        
        inbounds = await self.get_inbounds()
        
        for inbound in inbounds:
            if inbound_id and inbound.get("id") != inbound_id:
                continue
            
            # گرفتن clientStats از inbound
            client_stats = inbound.get("clientStats", [])
            
            for stat in client_stats:
                up = stat.get("up", 0)
                down = stat.get("down", 0)
                total = up + down
                
                clients_traffic.append({
                    "email": stat.get("email"),
                    "inbound_id": stat.get("inboundId"),
                    "enable": stat.get("enable", True),
                    "upload_gb": round(up / (1024**3), 3),
                    "download_gb": round(down / (1024**3), 3),
                    "total_gb": round(total / (1024**3), 3)
                })
        
        return clients_traffic
    
    async def reset_client_traffic(self, inbound_id: int, email: str) -> dict:
        """ریست ترافیک کلاینت"""
        result = await self._request(
            "POST",
            f"/panel/api/inbounds/{inbound_id}/resetClientTraffic/{email}",
            {}
        )
        return result
    
    async def get_client_ips(self, email: str) -> dict:
        """دریافت IP های کلاینت"""
        result = await self._request(
            "POST",
            f"/panel/api/inbounds/clientIps/{email}",
            {}
        )
        return result
    
    # ==================== Helper Functions ====================
    
    async def get_client_by_email(self, email: str) -> dict:
        """پیدا کردن کلاینت با ایمیل"""
        inbounds = await self.get_inbounds()
        
        for inbound in inbounds:
            settings = json.loads(inbound.get("settings", "{}"))
            clients = settings.get("clients", [])
            
            for client in clients:
                if client.get("email") == email:
                    return {
                        "success": True,
                        "client": client,
                        "inbound_id": inbound.get("id"),
                        "inbound_remark": inbound.get("remark")
                    }
        
        return {"success": False, "msg": "Client not found"}
    
    async def get_subscription_link(self, inbound_id: int, email: str) -> str:
        """ساخت لینک اشتراک"""
        inbound = await self.get_inbound(inbound_id)
        if not inbound:
            return ""
        
        # پیدا کردن کلاینت
        settings = json.loads(inbound.get("settings", "{}"))
        clients = settings.get("clients", [])
        
        client = None
        for c in clients:
            if c.get("email") == email:
                client = c
                break
        
        if not client:
            return ""
        
        return f"{self.base_url}/sub/{client.get('subId', '')}"
    
    async def get_config_link(self, inbound_id: int, email: str, address: str = None) -> str:
        """ساخت لینک کامل کانفیگ (vless://, vmess://, trojan://)"""
        inbound = await self.get_inbound(inbound_id)
        if not inbound:
            return ""
        
        # پیدا کردن کلاینت
        settings = json.loads(inbound.get("settings", "{}"))
        clients = settings.get("clients", [])
        
        client = None
        for c in clients:
            if c.get("email") == email:
                client = c
                break
        
        if not client:
            return ""
        
        protocol = inbound.get("protocol", "vless")
        port = inbound.get("port", 443)
        remark = inbound.get("remark", "")
        
        # آدرس سرور
        if not address:
            # استخراج از URL پنل
            from urllib.parse import urlparse
            parsed = urlparse(self.base_url)
            address = parsed.hostname
        
        stream_settings = json.loads(inbound.get("streamSettings", "{}"))
        network = stream_settings.get("network", "tcp")
        security = stream_settings.get("security", "none")
        
        # ساخت لینک بر اساس پروتکل
        if protocol == "vless":
            return self._build_vless_link(client, address, port, remark, stream_settings, network, security)
        elif protocol == "vmess":
            return self._build_vmess_link(client, address, port, remark, stream_settings, network, security)
        elif protocol == "trojan":
            return self._build_trojan_link(client, address, port, remark, stream_settings, network, security)
        
        return ""
    
    def _build_vless_link(self, client: dict, address: str, port: int, 
                          remark: str, stream_settings: dict, network: str, security: str) -> str:
        """ساخت لینک VLESS"""
        from urllib.parse import quote
        
        uuid_str = client.get("id", "")
        email = client.get("email", "")
        flow = client.get("flow", "")
        
        params = [f"type={network}"]
        
        if security == "reality":
            params.append("security=reality")
            reality = stream_settings.get("realitySettings", {})
            reality_settings = reality.get("settings", {})
            
            # Public Key - اول از settings بخوان، بعد از root
            pbk = reality_settings.get("publicKey") or reality.get("publicKey") or ""
            if pbk:
                params.append(f"pbk={pbk}")
            
            # Fingerprint
            fp = reality_settings.get("fingerprint") or reality.get("fingerprint") or "chrome"
            if fp:
                params.append(f"fp={fp}")
            
            # Server names
            server_names = reality.get("serverNames", [])
            if server_names:
                params.append(f"sni={server_names[0]}")
            
            # Short IDs
            short_ids = reality.get("shortIds", [])
            if short_ids:
                params.append(f"sid={short_ids[0]}")
            
            # Spider X
            spider_x = reality_settings.get("spiderX") or reality.get("spiderX") or "/"
            if spider_x:
                params.append(f"spx={quote(spider_x, safe='')}")
                
        elif security == "tls":
            params.append("security=tls")
            tls_settings = stream_settings.get("tlsSettings", {})
            
            if tls_settings.get("serverName"):
                params.append(f"sni={tls_settings.get('serverName')}")
            if tls_settings.get("fingerprint"):
                params.append(f"fp={tls_settings.get('fingerprint')}")
            
            alpn = tls_settings.get("alpn", [])
            if alpn:
                params.append(f"alpn={quote(','.join(alpn))}")
        else:
            params.append("security=none")
        
        # تنظیمات شبکه
        if network == "ws":
            ws_settings = stream_settings.get("wsSettings", {})
            if ws_settings.get("path"):
                params.append(f"path={quote(ws_settings.get('path'))}")
            if ws_settings.get("headers", {}).get("Host"):
                params.append(f"host={ws_settings['headers']['Host']}")
                
        elif network == "grpc":
            grpc_settings = stream_settings.get("grpcSettings", {})
            if grpc_settings.get("serviceName"):
                params.append(f"serviceName={grpc_settings.get('serviceName')}")
            if grpc_settings.get("multiMode"):
                params.append("mode=multi")
                
        elif network == "tcp":
            tcp_settings = stream_settings.get("tcpSettings", {})
            header = tcp_settings.get("header", {})
            if header.get("type") == "http":
                params.append("headerType=http")
                request = header.get("request", {})
                if request.get("path"):
                    paths = request.get("path", [])
                    if paths:
                        params.append(f"path={quote(paths[0])}")
                if request.get("headers", {}).get("Host"):
                    hosts = request["headers"]["Host"]
                    if hosts:
                        params.append(f"host={hosts[0]}")
        
        if flow:
            params.append(f"flow={flow}")
        
        params.append("encryption=none")
        
        params_str = "&".join(params)
        fragment = f"{remark}-{email}" if remark else email
        
        return f"vless://{uuid_str}@{address}:{port}?{params_str}#{quote(fragment)}"
    
    def _build_vmess_link(self, client: dict, address: str, port: int,
                          remark: str, stream_settings: dict, network: str, security: str) -> str:
        """ساخت لینک VMess"""
        import base64
        
        email = client.get("email", "")
        
        vmess_config = {
            "v": "2",
            "ps": f"{remark}-{email}" if remark else email,
            "add": address,
            "port": str(port),
            "id": client.get("id", ""),
            "aid": str(client.get("alterId", 0)),
            "scy": client.get("security", "auto"),
            "net": network,
            "type": "none",
            "host": "",
            "path": "",
            "tls": security if security in ["tls", "xtls"] else "",
            "sni": "",
            "alpn": "",
            "fp": ""
        }
        
        if security == "tls":
            tls_settings = stream_settings.get("tlsSettings", {})
            vmess_config["sni"] = tls_settings.get("serverName", "")
            vmess_config["fp"] = tls_settings.get("fingerprint", "")
            alpn = tls_settings.get("alpn", [])
            if alpn:
                vmess_config["alpn"] = ",".join(alpn)
        
        if network == "ws":
            ws_settings = stream_settings.get("wsSettings", {})
            vmess_config["path"] = ws_settings.get("path", "")
            vmess_config["host"] = ws_settings.get("headers", {}).get("Host", "")
            
        elif network == "grpc":
            grpc_settings = stream_settings.get("grpcSettings", {})
            vmess_config["path"] = grpc_settings.get("serviceName", "")
            vmess_config["type"] = "gun"
            
        elif network == "tcp":
            tcp_settings = stream_settings.get("tcpSettings", {})
            header = tcp_settings.get("header", {})
            if header.get("type") == "http":
                vmess_config["type"] = "http"
                request = header.get("request", {})
                paths = request.get("path", [])
                if paths:
                    vmess_config["path"] = paths[0]
                hosts = request.get("headers", {}).get("Host", [])
                if hosts:
                    vmess_config["host"] = hosts[0]
        
        config_json = json.dumps(vmess_config, separators=(',', ':'))
        encoded = base64.b64encode(config_json.encode()).decode()
        
        return f"vmess://{encoded}"
    
    def _build_trojan_link(self, client: dict, address: str, port: int,
                           remark: str, stream_settings: dict, network: str, security: str) -> str:
        """ساخت لینک Trojan"""
        from urllib.parse import quote
        
        password = client.get("password", "")
        email = client.get("email", "")
        
        params = [f"type={network}"]
        
        if security == "tls":
            params.append("security=tls")
            tls_settings = stream_settings.get("tlsSettings", {})
            if tls_settings.get("serverName"):
                params.append(f"sni={tls_settings.get('serverName')}")
            if tls_settings.get("fingerprint"):
                params.append(f"fp={tls_settings.get('fingerprint')}")
            alpn = tls_settings.get("alpn", [])
            if alpn:
                params.append(f"alpn={quote(','.join(alpn))}")
                
        elif security == "reality":
            params.append("security=reality")
            reality = stream_settings.get("realitySettings", {})
            if reality.get("publicKey"):
                params.append(f"pbk={reality.get('publicKey')}")
            if reality.get("fingerprint"):
                params.append(f"fp={reality.get('fingerprint')}")
            server_names = reality.get("serverNames", [])
            if server_names:
                params.append(f"sni={server_names[0]}")
            short_ids = reality.get("shortIds", [])
            if short_ids:
                params.append(f"sid={short_ids[0]}")
        
        if network == "ws":
            ws_settings = stream_settings.get("wsSettings", {})
            if ws_settings.get("path"):
                params.append(f"path={quote(ws_settings.get('path'))}")
            if ws_settings.get("headers", {}).get("Host"):
                params.append(f"host={ws_settings['headers']['Host']}")
                
        elif network == "grpc":
            grpc_settings = stream_settings.get("grpcSettings", {})
            if grpc_settings.get("serviceName"):
                params.append(f"serviceName={grpc_settings.get('serviceName')}")
        
        params_str = "&".join(params)
        fragment = f"{remark}-{email}" if remark else email
        
        return f"trojan://{password}@{address}:{port}?{params_str}#{quote(fragment)}"


# تابع کمکی برای استفاده ساده
async def get_panel() -> Panel3XUI:
    """ایجاد و برگرداندن نمونه پنل"""
    panel = Panel3XUI()
    await panel.create_session()
    await panel.login()
    return panel

"""
================================================================================
           JWT 鉴权三层学习指南 —— 基于 Travel Planner 项目实战
================================================================================

本文件逐层剖析 JWT 鉴权的完整链路，从前端到后端，从登录到校验。

链路全景：
    前端请求                         后端
   ┌──────────────┐              ┌──────────────────────────────┐
   │  axios 拦截器  │  ──→ 请求头  │  FastAPI 依赖注入系统          │
   │  + Bearer 令牌 │  ──→ 带上  │  ├─ OAuth2PasswordBearer     │
   └──────────────┘              │  │  (从Header取原始token)     │
                                 │  ├─ get_current_user         │
                                 │  │  (解码JWT，查数据库)      │
                                 │  └─ get_current_active_user  │
                                 │     (校验is_active)          │
                                 └──────────────────────────────┘

运行方式：
    python study/study_jwt_auth.py

不需要数据库，本文件包含独立的 JWT 编解码实现。
"""

import json
import time
import hashlib
import base64
import hmac
from typing import Optional


# ============================================================================
#   Part 0: 前置知识 —— 什么是 JWT？
# ============================================================================
#
# JWT（JSON Web Token）是一个"自包含"的令牌，形式是：
#   xxxxx.yyyyy.zzzzz
#   ↑header ↑payload ↑signature
#
# 为什么叫"自包含"？
#   因为 token 本身就已经包含了用户信息（如 email、过期时间），
#   后端收到 token 后，不需要再查数据库（除非想看用户是否被禁用）。
#
# 三个部分：
#   Header:     {"alg": "HS256", "typ": "JWT"}  → 怎么加密的
#   Payload:    {"sub": "user@email.com", "exp": 1700000000}  → 用户信息
#   Signature:  HMACSHA256(base64(header) + "." + base64(payload), secret)
#              → 防篡改签名


# ============================================================================
#   Part 1: 底层原理 —— 手写一个简易 JWT
# ============================================================================
#
# 先把 JWT 的"黑盒"拆开，看看里面到底怎么工作的。

# ── 1.1 Base64 URL 编码 ────────────────────────────────────────────────────
# JWT 用的是 base64url（不是标准 base64），区别：
#   标准 base64: + / =
#   base64url:   - _ （去掉末尾的 =）

def base64url_encode(data: bytes) -> str:
    """将 bytes 编码为 base64url 字符串（去掉末尾的 =）"""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def base64url_decode(s: str) -> bytes:
    """将 base64url 字符串解码为 bytes（补回 =）"""
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


# ── 1.2 HMAC-SHA256 签名 ────────────────────────────────────────────────────
# 项目用的是 HS256 算法（对称加密）。
# 含义：用一个密钥对"header.payload"字符串进行 HMAC-SHA256 哈希。

def hmac_sha256_sign(message: str, secret: str) -> str:
    """用密钥对消息进行 HMAC-SHA256 签名"""
    signature = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64url_encode(signature)


# ── 1.3 手写 JWT 编码 ──────────────────────────────────────────────────────

def manual_jwt_encode(payload: dict, secret: str) -> str:
    """
    手动生成 JWT token —— 和 python-jose 库做一样的事
    
    步骤：
        1. 构造 header: {"alg": "HS256", "typ": "JWT"}
        2. 构造 payload: {"sub": "xxx", "exp": 123456, ...}
        3. 分别 base64url 编码 header 和 payload
        4. 用密钥对 "header.payload" 做 HMAC-SHA256 签名
        5. 拼接成 "header.payload.signature"
    """
    # Step 1: Header
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")).encode())

    # Step 2: Payload
    payload_b64 = base64url_encode(json.dumps(payload, separators=(",", ":")).encode())

    # Step 3: 签名
    message = f"{header_b64}.{payload_b64}"
    signature = hmac_sha256_sign(message, secret)

    # Step 4: 拼接
    token = f"{message}.{signature}"
    return token


# ── 1.4 手写 JWT 解码 ──────────────────────────────────────────────────────

def manual_jwt_decode(token: str, secret: str) -> Optional[dict]:
    """
    手动解码 JWT token
    
    步骤：
        1. 按 . 分割成三部分
        2. 用 header.payload 重新计算签名，和传过来的签名对比
        3. 如果签名不匹配 → 说明 token 被篡改 → 返回 None
        4. 如果签名匹配 → 解码 payload，检查是否过期
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            print("  ❌ token 格式错误：应该有三个部分")
            return None

        header_b64, payload_b64, signature_b64 = parts

        # Step 1: 验证签名
        expected_signature = hmac_sha256_sign(f"{header_b64}.{payload_b64}", secret)
        # 注意：要用 hmac.compare_digest 防止时序攻击
        if not hmac.compare_digest(signature_b64, expected_signature):
            print("  ❌ 签名不匹配：token 可能被篡改")
            return None

        # Step 2: 解码 payload
        payload_bytes = base64url_decode(payload_b64)
        payload = json.loads(payload_bytes)

        # Step 3: 检查过期
        exp = payload.get("exp", 0)
        now = time.time()
        if now > exp:
            print(f"  ❌ token 已过期（exp={exp}, now={now}）")
            return None

        print(f"  ✅ token 有效，剩余 {int(exp - now)} 秒过期")
        return payload

    except Exception as e:
        print(f"  ❌ 解码失败: {e}")
        return None


def demo_manual_jwt():
    """演示手写 JWT 的编解码过程"""
    print("\n" + "=" * 60)
    print("  [PART 1] 手写 JWT 编解码")
    print("=" * 60)

    SECRET = "my-secret-key"
    payload = {
        "sub": "alice@example.com",
        "exp": int(time.time()) + 3600,  # 1小时后过期
        "iat": int(time.time()),
    }

    print(f"\n  原始 payload: {payload}")
    print(f"  密钥: {SECRET}")

    # 编码
    token = manual_jwt_encode(payload, SECRET)
    print(f"\n  生成的 token:")
    print(f"  {token}")

    # 解码显示各部分
    parts = token.split(".")
    print(f"\n  ┌─ Header:   {parts[0]}")
    print(f"  ├─ Payload:  {parts[1]}")
    print(f"  └─ Signature: {parts[2][:20]}...（截断）")

    # 解码校验
    print(f"\n  ▶ 正确解码:")
    decoded = manual_jwt_decode(token, SECRET)
    print(f"  decoded: {decoded}")

    # 篡改测试
    print(f"\n  ▶ 篡改测试: 修改 payload 中的 email")
    tampered = token.replace("alice", "bob")
    manual_jwt_decode(tampered, SECRET)

    # 错误密钥测试
    print(f"\n  ▶ 密钥错误测试: 用 wrong-secret 解码")
    manual_jwt_decode(token, "wrong-secret")


# ============================================================================
#   Part 2: 项目中的真实实现（对应 services/auth.py）
# ============================================================================
#
# 项目中用 python-jose 库，省去了手写那些 base64/HMAC 的麻烦。
# 核心代码只有几行，但你要理解它的每一步在做什么。

# ── 2.1 安装依赖 ───────────────────────────────────────────────────────────
# 项目中对应的依赖（requirements.txt）：
#   python-jose[cryptography]==3.3.0
#   passlib[bcrypt]==1.7.4
#   bcrypt==4.2.0

# 如果安装了这些库，可以取消注释下面的 import 来运行
# 如果没安装，我们继续用手写版本模拟

try:
    from jose import JWTError, jwt
    JOSE_AVAILABLE = True
except ImportError:
    JOSE_AVAILABLE = False
    # 模拟 jose 的接口
    class JWTError(Exception):
        pass

    class jwt:
        @staticmethod
        def encode(claims, key, algorithm):
            return manual_jwt_encode(claims, key)

        @staticmethod
        def decode(token, key, algorithms):
            payload = manual_jwt_decode(token, key)
            if payload is None:
                raise JWTError("Invalid token")
            return payload


# ── 2.2 项目中的配置 ───────────────────────────────────────────────────────
# 对应 schemas/config.py

class Settings:
    """模拟 settings 对象"""
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 天
    API_V1_STR: str = "/api/v1"

settings = Settings()


# ── 2.3 密码哈希 ────────────────────────────────────────────────────────────
# 项目中用 passlib 的 bcrypt 算法
# 这里的实现只是演示，实际用的是 passlib 库

try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    PASSLIB_AVAILABLE = True
except ImportError:
    PASSLIB_AVAILABLE = False
    # 模拟 passlib（简化版，实际用 bcrypt 算法）
    class FakePwdContext:
        def hash(self, password):
            return f"hashed:{password}"

        def verify(self, password, hashed):
            return hashed == f"hashed:{password}"

    pwd_context = FakePwdContext()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码 —— 项目中的原始代码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """密码哈希 —— 项目中的原始代码"""
    return pwd_context.hash(password)


# ── 2.4 生成 Access Token（项目中的原始代码） ───────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[float] = None) -> str:
    """
    项目 services/auth.py 的原始代码

    参数：
        data: 要编码到 token 中的数据，比如 {"sub": user.email}
        expires_delta: 过期时间（秒），不传则用默认的 8 天

    返回：
        JWT 字符串

    关键点：
        data 中的 "sub" 字段是 JWT 标准字段，表示"subjct"（主体）。
        这里用 email 作为 sub，因为 email 在系统中是唯一的。
    """
    to_encode = data.copy()

    # 计算过期时间
    if expires_delta:
        expire = time.time() + expires_delta
    else:
        expire = time.time() + settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    to_encode.update({"exp": expire})
    # 标准 JWT 声明（Registered Claims）：
    #   sub (Subject):  主体，通常是用户标识
    #   exp (Expiration): 过期时间（Unix 时间戳）
    #   iat (Issued At): 签发时间
    #   iss (Issuer):    签发者
    #   aud (Audience):  受众
    # 项目中只用到了 sub 和 exp

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


# ── 2.5 解码 Access Token（项目中的原始代码） ───────────────────────────────

def decode_access_token(token: str) -> Optional[dict]:
    """
    解码 JWT token —— 对应 get_current_user 中的逻辑

    步骤：
        1. 用 SECRET_KEY 解码 token
        2. 如果解码失败（签名错误、过期等），抛 JWTError
        3. 从 payload 中取出 sub（email）
        4. 如果 sub 为空，说明 token 无效
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        return payload
    except JWTError:
        return None


def demo_create_and_decode():
    """演示项目中 token 的生成和解析"""
    print("\n" + "=" * 60)
    print("  [PART 2] 项目中的 JWT 实现")
    print("=" * 60)

    # ── 生成 token ──────────────────────────────────────────────────────
    user_email = "alice@example.com"
    print(f"\n  用户: {user_email}")

    token = create_access_token(
        data={"sub": user_email},
        expires_delta=3600,  # 1 小时过期，方便测试
    )
    print(f"  token 前 50 位: {token[:50]}...")

    # ── 解码 token ──────────────────────────────────────────────────────
    payload = decode_access_token(token)
    if payload:
        print(f"  解码 payload: {payload}")
        print(f"  sub (email): {payload.get('sub')}")
        exp_remaining = int(payload.get("exp", 0) - time.time())
        print(f"  剩余有效时间: {exp_remaining} 秒")


# ============================================================================
#   Part 3: 第一层 —— 前端请求拦截器（对应 frontend/src/api/index.ts）
# ============================================================================
#
# 前端在每次请求时自动带上 token，这个工作由 axios 拦截器完成。

def demo_frontend_interceptor():
    """
    模拟前端拦截器的工作方式

    前端代码（api/index.ts）：
        api.interceptors.request.use(
            (config) => {
                const token = localStorage.getItem('token')
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`
                }
                return config
            },
        )

    核心逻辑：
        1. 从 localStorage 取出 token（登录时存进去的）
        2. 如果 token 存在，加到请求头的 Authorization 字段
        3. 格式: "Bearer <token>"
    """
    print("\n" + "=" * 60)
    print("  [PART 3] 第一层：前端请求拦截器")
    print("=" * 60)

    # 模拟前端 localStorage
    class LocalStorage:
        """模拟浏览器的 localStorage"""
        def __init__(self):
            self._data = {}

        def setItem(self, key, value):
            self._data[key] = value
            print(f"  ✅ localStorage.setItem('{key}', '...{value[-10:]}')")

        def getItem(self, key):
            value = self._data.get(key)
            print(f"  📖 localStorage.getItem('{key}') → {'找到' if value else '未找到'}")
            return value

        def removeItem(self, key):
            self._data.pop(key, None)
            print(f"  🗑 localStorage.removeItem('{key}')")

    storage = LocalStorage()

    # ── 模拟登录过程 ────────────────────────────────────────────────────
    print("\n  ▶ 模拟登录流程:")

    # 1. 用户登录成功，后端返回 token
    token = create_access_token({"sub": "alice@example.com"})
    print(f"  ① 后端返回 token")

    # 2. 前端保存 token
    storage.setItem("token", token)
    print(f"  ② 前端保存 token 到 localStorage")

    # 3. 发起请求时，拦截器自动加头
    print(f"\n  ▶ 发起请求时（拦截器自动执行）:")

    config = {"headers": {}, "url": "/api/v1/trips"}
    print(f"  原始请求头: {config['headers']}")

    # 这就是拦截器做的事
    stored_token = storage.getItem("token")
    if stored_token:
        config["headers"]["Authorization"] = f"Bearer {stored_token}"

    print(f"  添加后请求头: {config['headers']}")
    print(f"  实际 HTTP 请求头:")
    print(f"    Authorization: Bearer eyJ...")

    # ── 模拟 401 响应 ──────────────────────────────────────────────────
    print(f"\n  ▶ 后端返回 401 时（响应拦截器）:")

    # 前端代码中的响应拦截器
    def response_interceptor(error):
        if error.get("status") == 401:
            storage.removeItem("token")
            print(f"  ⚠ token 失效，已清除，跳转登录页")
            # window.location.href = '/login'
        return None

    response_interceptor({"status": 401})


# ============================================================================
#   Part 4: 第二层 —— OAuth2PasswordBearer（对应 services/auth.py）
# ============================================================================
#
# 这是 FastAPI 提供的一个"依赖"，它从请求中提取 token。
# 项目中的代码：
#   oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# ── 4.1 模拟 OAuth2PasswordBearer 的工作方式 ───────────────────────────────

class MockOAuth2PasswordBearer:
    """
    模拟 FastAPI 的 OAuth2PasswordBearer

    它的工作：
        1. 从请求头 Authorization 中取 token
        2. 格式必须是 "Bearer <token>"
        3. 如果不存在或格式不对，抛 401 异常
        4. tokenUrl 只是告诉前端"去哪里登录"，不影响后端逻辑

    它在 FastAPI 中的用法：
        async def get_current_user(token: str = Depends(oauth2_scheme)):
            # token 参数已经被 OAuth2PasswordBearer 提取好了
            # 你拿到的是纯字符串 token，不包括 "Bearer " 前缀
    """

    def __init__(self, token_url: str):
        self.token_url = token_url

    def __call__(self, headers: dict) -> Optional[str]:
        """
        模拟 FastAPI 的依赖注入调用

        参数：
            headers: 模拟 HTTP 请求头
        
        返回：
            提取出的 token 字符串，如果无效则返回 None
        """
        auth_header = headers.get("Authorization", "")

        if not auth_header:
            print("  ❌ 未提供 Authorization 头")
            return None

        # 检查格式：必须是 "Bearer <token>"
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            print(f"  ❌ Authorization 格式错误: {auth_header}")
            print(f"     正确格式: Bearer <token>")
            return None

        token = parts[1]
        print(f"  ✅ 成功提取 token: {token[:30]}...")
        return token


def demo_oauth2_scheme():
    """演示 OAuth2PasswordBearer 的工作方式"""
    print("\n" + "=" * 60)
    print("  [PART 4] 第二层：OAuth2PasswordBearer")
    print("=" * 60)

    # 创建模拟的 OAuth2PasswordBearer
    # 项目中的写法：
    #   oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
    oauth2_scheme = MockOAuth2PasswordBearer(token_url="/api/v1/auth/login")

    print(f"\n  tokenUrl = {oauth2_scheme.token_url}")
    print(f"  （这个 URL 告诉前端去哪里获取 token，不影响后端校验逻辑）")

    # ── 测试各种请求头 ──────────────────────────────────────────────────
    test_cases = [
        ("✅ 正确格式", {"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhbGljZUBleGFtcGxlLmNvbSJ9.abc"}),
        ("❌ 没有 Bearer", {"Authorization": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhbGljZUBleGFtcGxlLmNvbSJ9.abc"}),
        ("❌ 格式错误(3段)", {"Authorization": "Bearer token1 token2"}),
        ("❌ 没有头", {}),
        ("❌ 大小写错误", {"Authorization": "bearer eyJhbGciOiJIUzI1NiJ9.xxx"}),
        # 注意：实际项目中大小写不敏感，所以 "bearer" 和 "Bearer" 都行
        # 这里用 .lower() 处理了，所以大小写都通过
    ]

    for desc, headers in test_cases:
        print(f"\n  {desc}")
        print(f"    请求头: {headers.get('Authorization', '（无）')}")
        token = oauth2_scheme(headers)


# ============================================================================
#   Part 5: 第三层 —— get_current_user + get_current_active_user
#            （对应 services/auth.py）
# ============================================================================
#
# 这是鉴权的"最后一公里"：把 token 中的信息变成真正的 User 对象。

# ── 5.1 模拟数据库 ─────────────────────────────────────────────────────────

# 模拟数据库中的用户表
FAKE_USERS_DB = {}

class MockUser:
    """模拟 User 模型"""
    def __init__(self, id: int, email: str, username: str, hashed_password: str, is_active: bool = True):
        self.id = id
        self.email = email
        self.username = username
        self.hashed_password = hashed_password
        self.is_active = is_active

    def __repr__(self):
        return f"User(id={self.id}, email={self.email}, active={self.is_active})"


# 初始化一个测试用户
def init_test_user():
    """初始化一个测试用户到模拟数据库"""
    user = MockUser(
        id=1,
        email="alice@example.com",
        username="alice",
        hashed_password=get_password_hash("password123"),
    )
    FAKE_USERS_DB[user.email] = user
    return user


# ── 5.2 get_current_user（项目中的原始代码） ────────────────────────────────
#
# 项目 services/auth.py 中的原始代码：
#
#   async def get_current_user(
#       token: str = Depends(oauth2_scheme),   # 第二层：取 token
#       db: AsyncSession = Depends(get_db),     # 数据库会话
#   ) -> User:
#       credentials_exception = HTTPException(
#           status_code=status.HTTP_401_UNAUTHORIZED,
#           detail="Could not validate credentials",
#           headers={"WWW-Authenticate": "Bearer"},
#       )
#       try:
#           payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
#           email: str = payload.get("sub")
#           if email is None:
#               raise credentials_exception
#       except JWTError:
#           raise credentials_exception
#
#       user = await get_user_by_email(db, email=email)
#       if user is None:
#           raise credentials_exception
#       return user

def get_current_user(token: str) -> Optional[MockUser]:
    """
    模拟项目的 get_current_user
    
    步骤：
        1. 解码 JWT → 拿到 payload
        2. 从 payload 中取 sub（email）
        3. 用 email 查数据库 → 拿到 User 对象
        4. 如果以上任何一步失败，返回 None（项目中抛 401 异常）
    """
    print(f"\n  ▶ get_current_user 开始执行...")

    # Step 1: 解码 JWT
    print(f"  ① 解码 JWT token...")
    payload = decode_access_token(token)
    if payload is None:
        print(f"     ❌ JWT 解码失败（签名错误或过期）")
        return None

    # Step 2: 取 sub
    email = payload.get("sub")
    print(f"  ② 从 payload 中提取 sub (email): {email}")
    if email is None:
        print(f"     ❌ payload 中没有 sub 字段")
        return None

    # Step 3: 查数据库
    print(f"  ③ 按 email 查询数据库: {email}")
    user = FAKE_USERS_DB.get(email)
    if user is None:
        print(f"     ❌ 数据库中未找到该用户")
        return None

    print(f"  ④ 找到用户: {user}")
    return user


# ── 5.3 get_current_active_user（项目中的原始代码） ──────────────────────────
#
# 项目 services/auth.py 中的原始代码：
#
#   async def get_current_active_user(
#       current_user: User = Depends(get_current_user),  # 先调第三层
#   ) -> User:
#       if not current_user.is_active:
#           raise HTTPException(status_code=400, detail="Inactive user")
#       return current_user

def get_current_active_user(token: str) -> Optional[MockUser]:
    """
    模拟项目的 get_current_active_user
    
    在 get_current_user 的基础上，多检查一步：
        - 用户是否被禁用（is_active 是否为 False）
    """
    print(f"\n  ▶ get_current_active_user 开始执行...")

    # 先调用 get_current_user
    user = get_current_user(token)
    if user is None:
        return None

    # 再检查 is_active
    print(f"  ⑤ 检查用户是否活跃: is_active={user.is_active}")
    if not user.is_active:
        print(f"     ❌ 用户已被禁用（is_active=False）")
        return None

    print(f"  ✅ 用户验证通过！")
    return user


def demo_auth_chain():
    """演示完整的鉴权链路"""
    print("\n" + "=" * 60)
    print("  [PART 5] 完整的鉴权链路")
    print("=" * 60)

    # 先初始化测试用户
    user = init_test_user()
    print(f"  测试用户: {user}")

    # ── 场景 1: 正常登录 ─────────────────────────────────────────────────
    print("\n" + "─" * 50)
    print("  场景 1: 正常登录和请求")
    print("─" * 50)

    # 1. 登录 → 生成 token
    print(f"\n  🔑 登录阶段:")
    token = create_access_token({"sub": "alice@example.com"})
    print(f"  生成 token")

    # 2. 携带 token 请求受保护资源
    print(f"\n  📡 请求受保护资源:")

    # 模拟前端拦截器
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  请求头: Authorization: Bearer ...{token[-10:]}")

    # 模拟 OAuth2PasswordBearer（从 header 取 token）
    print(f"\n  🔍 OAuth2PasswordBearer 提取 token:")
    oauth2 = MockOAuth2PasswordBearer("/api/v1/auth/login")
    extracted_token = oauth2(headers)

    # 模拟 get_current_active_user（校验）
    if extracted_token:
        print(f"\n  👤 get_current_active_user 校验:")
        result = get_current_active_user(extracted_token)
        if result:
            print(f"\n  🎉 最终结果: {result.username} 的请求已通过鉴权！")

    # ── 场景 2: 无效 token ──────────────────────────────────────────────
    print("\n" + "─" * 50)
    print("  场景 2: 无效 token（过期/篡改）")
    print("─" * 50)

    bad_token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhbGljZUBleGFtcGxlLmNvbSJ9.invalid"
    headers = {"Authorization": f"Bearer {bad_token}"}

    extracted = oauth2(headers)
    if extracted:
        get_current_active_user(extracted)

    # ── 场景 3: 用户被禁用 ──────────────────────────────────────────────
    print("\n" + "─" * 50)
    print("  场景 3: 用户被禁用")
    print("─" * 50)

    # 禁用一个用户
    FAKE_USERS_DB["alice@example.com"].is_active = False
    print(f"  用户 is_active 已设为 False")

    token = create_access_token({"sub": "alice@example.com"})
    headers = {"Authorization": f"Bearer {token}"}
    extracted = oauth2(headers)
    if extracted:
        get_current_active_user(extracted)

    # 恢复
    FAKE_USERS_DB["alice@example.com"].is_active = True


# ============================================================================
#   Part 6: 完整请求链路 —— 从头到尾走一遍
# ============================================================================

async def demo_complete_flow():
    """
    模拟一个完整的 HTTP 请求，从浏览器到后端再回来

    场景：登录后访问 /api/v1/trips（获取行程列表）
    """
    print("\n" + "=" * 60)
    print("  [PART 6] 完整请求链路模拟")
    print("=" * 60)

    print("""
    ┌─────────────────────────────────────────────────────────────┐
    │                    完整请求链路                                │
    ├─────────────────────────────────────────────────────────────┤
    │                                                             │
    │ ① 用户登录 → 后端返回 token                                  │
    │   POST /api/v1/auth/login                                   │
    │   → 200 {"access_token": "eyJ...", "token_type": "bearer"}  │
    │                                                             │
    │ ② 前端保存 token                                             │
    │   localStorage.setItem("token", "eyJ...")                    │
    │                                                             │
    │ ③ 发起请求 → 拦截器自动加头                                  │
    │   GET /api/v1/trips                                         │
    │   Authorization: Bearer eyJ...                              │
    │                                                             │
    │ ④ FastAPI 接收请求                                            │
    │   ├─ OAuth2PasswordBearer 从 header 取 token                │
    │   ├─ get_current_user 解码 JWT → 查数据库 → 得 User 对象      │
    │   └─ get_current_active_user 检查 is_active                 │
    │                                                             │
    │ ⑤ 路由处理函数拿到 current_user，执行正常业务逻辑                │
    │                                                             │
    │ ⑥ 返回 200 {"id": 1, "title": "北京之旅", ...}               │
    │                                                             │
    └─────────────────────────────────────────────────────────────┘
    """)

    # 模拟执行
    user = init_test_user()

    # Step 1: 登录
    print(" ① 用户登录")
    token = create_access_token({"sub": "alice@example.com"})
    print(f"    后端返回 token: {token[:50]}...")

    # Step 2: 前端保存
    print("\n ② 前端保存 token")
    print("    localStorage.setItem('token', token)")

    # Step 3: 发起请求
    print("\n ③ 发起 GET /api/v1/trips")
    config = {
        "method": "GET",
        "url": "/api/v1/trips",
        "headers": {"Authorization": f"Bearer {token}"},
    }
    print(f"    请求头: {config['headers']}")

    # Step 4: 后端鉴权
    print("\n ④ 后端鉴权流程")
    oauth2 = MockOAuth2PasswordBearer("/api/v1/auth/login")
    extracted = oauth2(config["headers"])
    if extracted:
        current_user = get_current_active_user(extracted)

    # Step 5: 业务处理
    if current_user:
        print(f"\n ⑤ 路由处理函数收到 current_user: {current_user}")
        print(f"    执行正常业务逻辑...")
        print(f"    查询 user_id={current_user.id} 的行程列表...")

    # Step 6: 返回结果
    print(f"\n ⑥ 返回 200 OK")
    print(f"    响应体: [")
    print(f"      {{'id': 1, 'title': '北京之旅', 'destination': '北京'}},")
    print(f"      {{'id': 2, 'title': '上海之旅', 'destination': '上海'}}")
    print(f"    ]")


# ============================================================================
#   Part 7: 常见陷阱与 FAQ
# ============================================================================

def faq():
    """常见问题"""
    print("\n" + "=" * 60)
    print("  [PART 7] 常见陷阱与 FAQ")
    print("=" * 60)

    faqs = [
        ("Q: token 过期了怎么办？",
         "A: 前端收到 401 后，清除 token 并跳转登录页让用户重新登录。"
         "如果需要无感刷新，可以额外实现 refresh token 机制。"),

        ("Q: 为什么要用 Bearer 前缀？",
         "A: Bearer 是 HTTP 标准认证方式之一。"
         "格式为 Authorization: Bearer <token>。"
         "其他方式还有：Basic（用户名密码 base64 编码）、Digest 等。"),

        ("Q: HS256 和 RS256 的区别？",
         "A: 项目用 HS256（对称加密）：编码和解码用同一个密钥。"
         "RS256（非对称加密）：用私钥编码，公钥解码。"
         "RS256 更安全，适合多服务间认证；HS256 更简单，适合单体应用。"),

        ("Q: 项目为什么用 email 作为 sub，而不是 user_id？",
         "A: 两者都可以。用 email 的好处是即使用户 ID 变了，token 仍然有效。"
         "用 user_id 的好处是即使 email 变了，token 仍然有效。"
         "项目中 email 是唯一且不可变的，所以用 email 做 sub。"),

        ("Q: 为什么 get_current_user 要查数据库？",
         "A: JWT 虽然可以自包含信息，但查数据库可以确认用户是否还在（没被删除）、"
         "是否被禁用（is_active）。"
         "如果追求极致性能，可以把用户信息也编码到 JWT 中，但安全性会降低。"),

        ("Q: 什么是 WWW-Authenticate 响应头？",
         "A: 当后端返回 401 时，加这个头告诉前端应该用什么方式认证。"
         "项目中的写法：headers={'WWW-Authenticate': 'Bearer'}。"
         "浏览器看到这个头，会自动弹出登录框（但 SPA 中一般由前端代码处理）。"),

        ("Q: 密码为什么用 bcrypt 而不是直接哈希？",
         "A: bcrypt 是"慢哈希"，故意设计得很慢（几十毫秒），"
         "让暴力破解的成本非常高。SHA256 太快了，一秒能算几亿次。"
         "项目中用 passlib 库，它自动管理盐值和迭代次数。"),
    ]

    for i, (q, a) in enumerate(faqs, 1):
        print(f"\n  ── FAQ {i} ──────────────────────────────────────")
        print(f"  {q}")
        print(f"  {a}")


# ============================================================================
#   Part 8: 三层架构图解
# ============================================================================

def architecture_diagram():
    """打印架构图"""
    print("\n" + "=" * 60)
    print("  [PART 8] 三层架构图解")
    print("=" * 60)

    print("""
    ┌──────────────────────────────────────────────────────────────────┐
    │                        前端 (Vue 3)                             │
    │                                                                  │
    │  localStorage ──→ axios 拦截器 ──→ 请求头                        │
    │  "token"          自动添加          Authorization:               │
    │                    Bearer <token>   Bearer eyJ...                │
    └───────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼ HTTP 请求
    ┌──────────────────────────────────────────────────────────────────┐
    │                       后端 (FastAPI)                             │
    │                                                                  │
    │  路由定义:                                                       │
    │    @router.get("/trips")                                         │
    │    async def list_trips(                                         │
    │        db: Session = Depends(get_db),             ① 数据库会话    │
    │        current_user: User = Depends(              ② 鉴权！       │
    │            get_current_active_user                              │
    │        ),                                                        │
    │    ):                                                           │
    │                                                                  │
    │  依赖链:                                                         │
    │    get_current_active_user                                       │
    │      └─ Depends(get_current_user)                 ③ 第三层       │
    │           ├─ token = Depends(oauth2_scheme)       ② 第二层       │
    │           │    └─ 从 Header 取 "Bearer <token>"                  │
    │           ├─ payload = jwt.decode(token, SECRET)                 │
    │           ├─ email = payload.get("sub")                         │
    │           └─ user = db.query(User).where(email).first()          │
    │                                                                  │
    │  三层调用链:                                                     │
    │    Depends(oauth2_scheme)        → "Bearer eyJ..." → "eyJ..."    │
    │    Depends(get_current_user)     → "eyJ..." → User 对象          │
    │    Depends(get_current_active)   → User → 检查 is_active         │
    └──────────────────────────────────────────────────────────────────┘
    """)


# ============================================================================
#   主函数
# ============================================================================

async def main():
    """运行所有演示"""
    print("=" * 70)
    print("  JWT 鉴权三层学习之旅")
    print("  基于 Travel Planner 项目实战")
    print("=" * 70)

    # Part 1: 手写 JWT 理解底层原理
    demo_manual_jwt()

    # Part 2: 项目中的 JWT 实现
    demo_create_and_decode()

    # Part 3: 前端拦截器
    demo_frontend_interceptor()

    # Part 4: OAuth2PasswordBearer
    demo_oauth2_scheme()

    # Part 5: 完整的鉴权链路
    demo_auth_chain()

    # Part 6: 完整请求链路
    await demo_complete_flow()

    # Part 7: FAQ
    faq()

    # Part 8: 架构图
    architecture_diagram()

    print("\n" + "=" * 70)
    print("  🎉 学习完成！")
    print("=" * 70)
    print("""
  建议下一步：
    1. 打开 frontend/src/api/index.ts 看前端拦截器
    2. 打开 backend/app/services/auth.py 看完整鉴权代码
    3. 打开 backend/app/api/auth.py 看登录注册接口
    4. 打开 backend/app/api/trips.py 看如何在路由中使用鉴权依赖
    """)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
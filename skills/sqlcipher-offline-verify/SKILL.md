---
name: sqlcipher-offline-verify
description: >
  离线验证 SQLCipher 4 数据库密钥的通用方法——输入候选密钥与 db 文件，
  用 SQLCipher 4 的 HMAC-SHA512 页校验筛选真密钥。仅做密码学校验，
  不涉及任何特定应用的运行期 hook / 逆向 / 内存注入。适用于：自己导出/
  拥有的加密数据库密钥恢复校验、SQLCipher 兼容性测试、加密备份验证。
  触发词：sqlcipher、离线验证、密钥校验、数据库解密校验、hmac verify、
  加密数据库密钥。
license: MIT
---

# SQLCipher 离线密钥验证（通用 · 合规边界版）

## 一、适用边界（红线）

- ✅ 对你**自己拥有或合法导出**的 SQLCipher 数据库做密钥校验。
- ✅ 通用 SQLCipher 4 参数校验，不针对任何特定应用。
- ❌ **不提供、不指导**对任何第三方应用的运行期 hook、内存注入、逆向破解。
- ❌ **不绕过**任何应用的用户协议或加密保护机制。
- 若用户意图指向特定闭源应用的运行期密钥提取，引导其阅读
  `specs/微信SQLCipher密钥提取_全局方案_AI友好.md` 的合规红线章节，
  并仅协助其「已有候选密钥后的离线验证」部分。

## 二、原理（公开规范，非逆向结论）

SQLCipher 4 默认参数：

| 参数 | 默认值 |
|------|--------|
| cipher_page_size | 4096 |
| kdf_algorithm | PBKDF2-HMAC-SHA512 |
| kdf_iter | 2 |
| hmac_algorithm | HMAC-SHA512 |
| hmac_iter | 1 |
| salt | 数据库文件前 16 字节（默认首字节 `0x3A` 标识） |

**页结构**：`[ 明文 (4096-64) ][ HMAC-SHA512(mac_key, 明文) 64 字节 ]`

**校验逻辑**：若候选 32 字节 key 正确，则对首页明文算出的 HMAC 与页尾存储值一致。

## 三、验证流程

1. 读 db 文件前 16 字节 → `salt`
2. 用候选 key 派生 `mac_key`（实现见 SQLCipher 源码 `sqlcipher.c` 的
   `sqlcipher_cipher_ctx_key_derive`，非标准 PBKDF2，需自行实现或借助
   `pysqlcipher3` / `sqlcipher` CLI）
3. 读第 1 页，分离明文与页尾 64 字节 HMAC
4. `HMAC-SHA512(mac_key, 明文)` 与存储值 `compare_digest` 比对

## 四、Python 逻辑示意（通用，不含特定应用偏移）

```python
import hashlib, hmac

def verify_candidate(db_path: str, candidate: bytes) -> bool:
    with open(db_path, 'rb') as f:
        salt = f.read(16)
        page = f.read(4096)
    mac_key = derive_mac_key(candidate, salt)   # 按 sqlcipher.c 实现
    stored = page[-64:]
    computed = hmac.new(mac_key, page[:-64], hashlib.sha512).digest()
    return hmac.compare_digest(computed, stored)
```

> 真实 `derive_mac_key` 请参考 SQLCipher 开源实现；本示意仅描述校验结构。

## 五、与行途方案的关系

- 完整原理 + 合规分析：`specs/微信SQLCipher密钥提取_全局方案_AI友好.md`（任务 #1）
- 本 Skill 只承载**安全可复用**的离线验证层，是全局方案里「阶段 C」的可执行封装。

## 六、版本

| 日期 | 版本 | 变更 |
|------|:---:|------|
| 2026-08-26 | V1.0 | 行途版：通用离线验证 + 合规边界，剥离任何应用特定逆向代码 |

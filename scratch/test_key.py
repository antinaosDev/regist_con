
import base64
import re
from cryptography.hazmat.primitives import serialization

pk = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC1b8/DqzZPYaZC
puf5y+rdDrjwkPA/ueer0hR0Ig0vSHmeGSEWTLPV/s3GOQ2WGZJmk+HOqb290bWz
6Mf5KXm98CXhBRlrG48Oo+edbZixLop9uizZDyjOkFc5FnRxBtPhxEPHYFbWPu5U
Pyaut549bUnRJIHX5hDy/sg1en1UBHa8DHoGtpvmrw8p26S9nzFmJMlrPhTYGNQw
m6A2PRYj6FEcLW2TFHZJYXunQBbFxt6tTZ8/xo0VTTRA7m/3rNd6VCq1A6V/BtB8
BpbjOFSWgAPQ//oQcg436uBI21Fx0Lb0k6dmMfmo4gGQJEoGxc3vt1mdIjpKzhZC
ZuIw5/LBAgMBAAECggEAFem/btswl8VMMowcg9WuU80Jpppmvdea5KxehokvTPjk
oWTZE2uno66e1TRCURDdFvEA6ngjP7gCiUxRzKTG/JryxDrcr0w4irTejiu0r5+W
n+k6reuQCuSxeCZfYWBI+mE9K2kWC9G1cKzg4+Su4q3eprkRSo1RmjuN3DGjTeB5
DKPNYz39VKP8soKpGIVpYlGPqeC4GSrzOlrnLEun2iZX12SKXHsYYR4EzbdsLNNo
mg+h0EHK/OkxDl5LRohHQ5KsvdydYPu2UNwMRNSkuKC0vSDGn6TLAyWf/6/LOy2n
JoTX0R5jsfnNC3yjoYlVzi15fonLER83ZpN0w/uyMQKBgQDfDz4bmHIjAifRPakF
UPSmOidzCN6PzA04CdG7iG7RQRWfR7U8PhLrajs5XUSbuZ57e6R6FFfRe/k36O6I
xuqZ1hNJeAcUl0dEC+hknqk0SndysyFF1kxhj2m0Io0SH1FfIoLu3pLzKvmpKbBK
J0IMUEzDelBRONXpWW6Sh+ucuQKBgQDQOwV++VxlNT7Gf2Cigd/naeUpcjd69bYR
LGdouCkyE7XvKxAIe41AQBd5C6irvUeLOiB+WZcSg16kyD/jaXhFjd/TWp345Ejd
nn6ySkmkfNGrosJFKuFGGqFajHrhNLpWuYUt8DvG1DKLAWzVGdpq3dWkPkOWai4cz
rzf/ui1SSQKBgF+ALCwucbeRZbDNQH9ZMNW2kktLIdbZG1PByH0NJb0Lq5E9Z1f6
j6khG2gtCYHO0A64Wiw2Z372IDaS0QXYfHsOz8Ul0Yo8VrPIkV/7GiCcPVXrYbR/
0sX2W+BW5qU6qWEc6ogQ3UOlQ6zsf2DQPBP/kU4kIR0VQ2ib9J5h+TtpAoGAehgR
WekmhuVYgJUReVfDjHHn/4xMAZnu/lTV8W4CIa2zAKB0TzT6lpC98qimZsSeHYGg
qdUoIp/Kr74Gz/X4onfUpJ2+gMCCBQjp7CtS3gwjH3rgRjqa+uTbn9uUXxUQiOXd
l8k/alQVXcpdC4rhnu6GAq2IIzzqsqBrqlNk3ZkCgYEAsXUzbbdAqhgMoj+lHa1K
Ehll2QOJT4oEBEWm4S1tTMab2bEbB+u30/Lj0NbQQsCjXjFEUMgcQxIlGptYWqJ8
kRLTODB03vAsCAstZj0iKyplGYbeAesNoSuPEuiNoS8IAFwXRBB/5MuV8lsLTv56
UzAHC5RFhMcJKtt10G6sWfQ=
-----END PRIVATE KEY-----"""

def clean(pk):
    header = "-----BEGIN PRIVATE KEY-----"
    footer = "-----END PRIVATE KEY-----"
    body = pk.replace(header, "").replace(footer, "")
    body = body.replace('\\\\n', '').replace('\\n', '').replace('\n', '').replace('\r', '').replace(' ', '')
    body = re.sub(r'[^A-Za-z0-9+/]', '', body)
    missing = len(body) % 4
    if missing:
        body += '=' * (4 - missing)
    wrapped = "\n".join(body[i:i+64] for i in range(0, len(body), 64))
    return f"{header}\n{wrapped}\n{footer}\n"

cleaned = clean(pk)
print(f"Cleaned length: {len(cleaned)}")

try:
    header = "-----BEGIN PRIVATE KEY-----"
    footer = "-----END PRIVATE KEY-----"
    body = pk.replace(header, "").replace(footer, "").replace("\n", "").replace(" ", "").replace("\r", "")
    body = re.sub(r'[^A-Za-z0-9+/]', '', body)
    missing = len(body) % 4
    if missing:
        body += '=' * (4 - missing)
    
    der = base64.b64decode(body)
    print(f"DER length: {len(der)} bytes")
    print(f"First 10 bytes (hex): {der[:10].hex()}")
    
    from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_der_private_key
    
    print("--- Testing PEM load ---")
    try:
        load_pem_private_key(cleaned.encode('ascii'), password=None)
        print("PEM SUCCESS")
    except Exception as e:
        print(f"PEM FAILED: {e}")

    print("--- Testing DER load ---")
    try:
        load_der_private_key(der, password=None)
        print("DER SUCCESS")
    except Exception as e:
        print(f"DER FAILED: {e}")
        import traceback
        traceback.print_exc()
except Exception as e:
    import traceback
    traceback.print_exc()

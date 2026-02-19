import base64
import io

import qrcode
import qrcode.image.svg


def otpauth_qr_data_uri(otpauth_uri: str) -> str:
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(otpauth_uri, image_factory=factory, box_size=6, border=2)
    buffer = io.BytesIO()
    img.save(buffer)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"

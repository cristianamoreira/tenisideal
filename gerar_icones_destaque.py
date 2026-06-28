import math, os
from PIL import Image, ImageDraw, ImageFont
W=H=1080
PRETO=(13,13,13); AMARELO=(200,255,0); BRANCO=(245,245,245)
def bebas(s):
    for p in ["BebasNeue.ttf","/tmp/BebasNeue.ttf"]:
        if os.path.exists(p): return ImageFont.truetype(p,s)
    return ImageFont.load_default()
def centro(d,y,t,f,c):
    w=d.textlength(t,font=f); d.text(((W-w)/2,y),t,font=f,fill=c)
def estrela(d,cx,cy,R,r):
    pts=[]
    for i in range(10):
        ang=-math.pi/2+i*math.pi/5
        rad=R if i%2==0 else r
        pts.append((cx+rad*math.cos(ang),cy+rad*math.sin(ang)))
    d.polygon(pts,fill=AMARELO)
def lampada(d,cx,cy):
    d.ellipse([cx-150,cy-180,cx+150,cy+120],fill=AMARELO)
    d.rectangle([cx-55,cy+90,cx+55,cy+175],fill=AMARELO)
    d.rectangle([cx-55,cy+185,cx+55,cy+210],fill=AMARELO)
def livro(d,cx,cy):
    d.polygon([(cx-210,cy-120),(cx-15,cy-90),(cx-15,cy+170),(cx-210,cy+140)],fill=AMARELO)
    d.polygon([(cx+210,cy-120),(cx+15,cy-90),(cx+15,cy+170),(cx+210,cy+140)],fill=AMARELO)
def tag(d,cx,cy):  # etiqueta de oferta
    d.rounded_rectangle([cx-170,cy-120,cx+150,cy+120],radius=30,fill=AMARELO)
    d.ellipse([cx+70,cy-60,cx+130,cy],fill=PRETO)
    f=bebas(150); t="%"; w=d.textlength(t,font=f); d.text((cx-w/2-30,cy-95),t,font=f,fill=PRETO)
icones=[
 ("OFERTAS", lambda d: tag(d,540,430)),
 ("FAQ",     lambda d: centro(d,250,"?",bebas(480),AMARELO)),
 ("DICAS",   lambda d: lampada(d,540,420)),
 ("REVIEWS", lambda d: estrela(d,540,430,200,90)),
 ("GUIAS",   lambda d: livro(d,540,430)),
]
for nome,fn in icones:
    img=Image.new("RGB",(W,H),PRETO); d=ImageDraw.Draw(img)
    d.ellipse([55,55,W-55,H-55],outline=AMARELO,width=10)
    fn(d)
    centro(d,720,nome,bebas(96),BRANCO)
    img.save(f"icones/{nome.lower()}.png","PNG")
print("5 ícones gerados em ./icones/")

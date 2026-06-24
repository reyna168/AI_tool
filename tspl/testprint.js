const net = require("net");
const { PRINTER_IP, PRINTER_PORT } = require("./config");

function printLabel() {

  const tspl = `
SIZE 100 mm,150 mm
GAP 3 mm,0
DIRECTION 1
REFERENCE 0,0

CLS

TEXT 30,30,"MSJH.TTF",0,24,24,"出庫單"

BARCODE 30,80,"128",80,1,0,2,4,"OUT20260622001"

TEXT 30,190,"MSJH.TTF",0,18,18,"單號：OUT20260622001"

TEXT 30,240,"MSJH.TTF",0,18,18,"客戶：王小明"

TEXT 30,290,"MSJH.TTF",0,18,18,"電話：0912-345678"

TEXT 30,340,"MSJH.TTF",0,18,18,"地址：台北市中山區"

TEXT 30,390,"MSJH.TTF",0,18,18,"產品：測試商品"

TEXT 30,440,"MSJH.TTF",0,18,18,"數量：10"

QRCODE 600,80,L,6,A,0,"OUT20260622001"

PRINT 1
`;

  const client = new net.Socket();

  client.connect(PRINTER_PORT, PRINTER_IP, () => {

    console.log("已連線印表機");

    client.write(Buffer.from(tspl, "utf8"));

    client.end();
  });

  client.on("error", err => {
    console.error(err);
  });

  client.on("close", () => {
    console.log("列印完成");
  });
}

printLabel();
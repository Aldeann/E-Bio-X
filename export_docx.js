const fs = require('fs');
const https = require('https');
const http = require('http');

function postJSON(url,obj){
  return new Promise((res,rej)=>{
    const u=new URL(url);
    const lib=u.protocol==='https:'?https:http;
    const data=Buffer.from(JSON.stringify(obj));
    const req=lib.request({hostname:u.hostname,port:u.port|| (u.protocol==='https:'?443:80),path:u.pathname,method:'POST',headers:{'Content-Type':'application/json','Content-Length':data.length}},r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>res({status:r.statusCode,body:d}));});
    req.on('error',rej);req.write(data);req.end();
  });
}
function getJSON(url,h){
  return new Promise((res,rej)=>{
    const u=new URL(url);
    const lib=u.protocol==='https:'?https:http;
    const req=lib.request({hostname:u.hostname,port:u.port|| (u.protocol==='https:'?443:80),path:u.pathname,method:'GET',headers:h||{}},r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>res({status:r.statusCode,body:d}));});
    req.on('error',rej);req.end();
  });
}

(async()=>{
  try{
    const gl=await postJSON('http://localhost:5000/api/login',{email:'guru1@ebiox.com',password:'123123123'});
    const tok=JSON.parse(gl.body).access_token;
    const m=await getJSON('http://localhost:5000/api/materials/107',{Authorization:'Bearer '+tok});
    const mj=JSON.parse(m.body);
    fs.writeFileSync('D:/Aldeann/virus_export.json', JSON.stringify(mj,null,2));
    console.log('saved');
  }catch(e){console.error('err');}
})();

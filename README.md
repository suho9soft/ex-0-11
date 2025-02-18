# ex-0-11

라즈베리 파이 /토니 and 파이썬 /MQTTX /카메라

1-5 토니 esp32반도체 입니다 잘 다운로드 하셔서 arduino 에서 esp32 세팅 하고요 라즈베리파이에 서 토니 and 비주월 코드로 실행해 보세요

IoT MQTT Panel 호환이 가능 합니다 핸드폰에 앱이 있습니다

카메라 도 토니에서 된니다 잘 세팅 하면 된니다

esp32반도체 안드로이드 Pydroid 3 에서 핸드폰 에서 led 켜짐 꺼짐 이 된니다

다른 편집기 사용: vi 대신 다른 텍스트 편집기인 nano를 사용해 볼 수 있습니다.

sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf

//아래 부분을 찾아서

bind-address = 127.0.0.1

//이렇게 바꿔주기(그리고 나서 저장)

bind-address = 0.0.0.0

//db접속

sudo mysql -u root

//사용자 계정생성

CREATE USER 'arduino'@'%' IDENTIFIED BY '123f5678';

//권한부여

GRANT CREATE, DROP, ALTER, SELECT, INSERT, UPDATE, DELETE ON *.* TO 'arduino'@'%';
FLUSH PRIVILEGES;


//데이터베이스 재부팅

sudo systemctl restart mariadb

//계정생성확인(로그인해보기)

sudo mysql -u arduino -p

//비밀번호입력

show databases;

SHOW TABLES;

DESC student;


INSERT INTO student (name, age, gender) VALUES ('홍길동', 20, '남성');

select * from student;

sudo mysql -u arduino -p

use python14;


SHOW TABLES;

desc rotary_data;

SELECT * FROM rotary_data;

DELETE FROM rotary_data;

desc dht11_data;

SELECT * FROM dht11_data;










# Роҳнамои насб (Тоҷикӣ)
1. Дар GitHub репозиторийи нав созед ва ҳамаи файлҳои ин ZIP-ро бор кунед.
2. Ба Actions равед -> «Build Android APK» -> Run workflow. Баъди анҷом APK-ро аз Artifacts зеркашӣ кунед.
3. Сервер: дар компютер/VPS `pip install -r server/requirements.txt`, баъд `SONI_DEV=1 SONI_SECRET=x uvicorn app.main:app --port 8000`.
4. Дар godot/scripts/net.gd суроғаи серверро иваз кунед (wss://...) ва дубора APK созед.

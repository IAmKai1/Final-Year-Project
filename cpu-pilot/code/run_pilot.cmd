@echo off
cd /d D:\CAPSTONE\Pilot-VoiceBackdoor\code
python -u 03_finetune.py backdoor 0 > ..\log_3_bd0.txt 2>&1
python -u 03_finetune.py benign 0 > ..\log_3_bn0.txt 2>&1
python -u 03_finetune.py backdoor 1 > ..\log_3_bd1.txt 2>&1
python -u 03_finetune.py benign 1 > ..\log_3_bn1.txt 2>&1
python -u 04_eval_audit.py > ..\log_4_eval.txt 2>&1
echo finished > ..\log_DONE.txt

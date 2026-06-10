//---------------------------------------------------------------------------

#include <vcl.h>
#pragma hdrstop

#include "GmpDog.h"
#include "FT_ET99_API.h"

//---------------------------------------------------------------------------


#define	  ET_SUCCESS				0x00			//����ִ�гɹ�
#define   ET_ACCESS_DENY            0x01			//���ʱ��ܾ���Ȩ�޲���
#define   ET_COMMUNICATIONS_ERROR   0x02			//ͨѶ����û�д��豸
#define   ET_INVALID_PARAMETER      0x03			//��Ч�Ĳ�������������
#define   ET_NOT_SET_PID            0x04			//û������PID
#define   ET_UNIT_NOT_FOUND 	    0x05			//��ָ�����豸ʧ��
#define   ET_HARD_ERROR             0x06			//Ӳ������
#define   ET_UNKNOWN                0x07			//һ���Դ���

unsigned char G_PID[10] = { "FAFF72AD" };
unsigned char G_PIN[18] = { "FAFF72AD" };
unsigned int  G_MAGIC   = 0xEAEA3636;

// 新密码狗的pid  FAFF72AD    pin码  9E51F8C6BD343D56
//---------------------------------------------------------------------------

GmpDog::GmpDog()
    : mHandle(NULL)
{

}

bool GmpDog::findDog()
{
    int count = 0;
    mLastError = et_FindToken(G_PID, &count);

    return (mLastError == ET_SUCCESS);
}

bool GmpDog::getBindId(AnsiString &bid)
{
    // 1. open
    if (!open()) {
        return false;
    }

    // 2. verify
    if (!verify()) {
        return false;
    }

    // 3. read
    // 3.1 read magic
    unsigned int magic_buf = 0;
    mLastError = et_Read(mHandle, 0, 4, (char*)&magic_buf);
    if (mLastError != ET_SUCCESS) {
        return false;
    }
    if (magic_buf != G_MAGIC) {
        bid = "new_dog";
        return true;
    }
    
    // 3.2 read length
    short sn_length      = 0;
    mLastError = et_Read(mHandle, 4, 2, (char*)&sn_length);
    if (mLastError != ET_SUCCESS) {
        return false;
    }

    // 3.3 read bid
    char  sn_buffer[255] = {0};
    mLastError = et_Read(mHandle, 6, sn_length, sn_buffer);
    if (mLastError != ET_SUCCESS) {
        return false;
    }
    bid = sn_buffer;

    return true;
}

bool GmpDog::setBindId(AnsiString bid)
{
    // 1. open
    if (!open()) {
        return false;
    }

    // 2. verify
    if (!verify(true)) {
        return false;
    }

    // 3. write
    // 3.1 magic
    mLastError = et_Write(mHandle, 0, 4, (char*)&G_MAGIC);
    if (mLastError != ET_SUCCESS) {
        return false;
    }
    
    // 3.2 length
    short sn_length      = bid.Length();
    mLastError = et_Write(mHandle, 4, 2, (char*)&sn_length);
    if (mLastError != ET_SUCCESS) {
        return false;
    }

    // 3.3 bid
    char  sn_buffer[255] = {0};
    strcpy(sn_buffer, bid.c_str());
    mLastError = et_Write(mHandle, 6, sn_length, sn_buffer);
    if (mLastError != ET_SUCCESS) {
        return false;
    }

    return true;
}

bool GmpDog::reset()
{
    // 1. open
    if (!open()) {
        return false;
    }

    // 2. verify
    if (!verify(true)) {
        return false;
    }

    // 3. write
    unsigned char buffer[50] = {0};
    mLastError = et_Write(mHandle, 0, 50, buffer);
    if (mLastError != ET_SUCCESS) {
        return false;
    }

    return true;
}

bool GmpDog::close()
{
    mLastError = et_CloseToken(mHandle);
    mHandle = NULL;

    return (mLastError == ET_SUCCESS);
}

bool GmpDog::open()
{
    int index = 1;
    mLastError = et_OpenToken(&mHandle, G_PID, index);
    return (mLastError == ET_SUCCESS);
}

bool GmpDog::verify(bool use_so /* = false */)
{
    if (use_so) {
        AnsiString tmp;

        tmp.sprintf("%ldDD%d7F%s", 576741, 21, "C401");
        mLastError = et_Verify(mHandle, ET_VERIFY_SOPIN, tmp.c_str());
    } else {
        mLastError = et_Verify(mHandle, ET_VERIFY_USERPIN, G_PIN);
    }
    return (mLastError == ET_SUCCESS);
}

AnsiString GmpDog::getLastError()
{
    AnsiString r = "";
    switch(mLastError)
	{
	case ET_SUCCESS :
		r = ("Success!");
        break;

	case ET_ACCESS_DENY :
		r = ("Err: access denied, have not enough right!");
        break;

	case ET_COMMUNICATIONS_ERROR :
		r = ("Err: have not open the device");
        break;

	case ET_INVALID_PARAMETER :
		r = ("Err: invalid parameter!");
        break;

	case ET_NOT_SET_PID	:
		r = ("Err: have not set PID!");
        break;

	case ET_UNIT_NOT_FOUND :
		r = ("Err: open the device fail!");
        break;

	case 0xF0 :
		r = ("Err: PIN have been locked!");
        break;

	default	:
		{
			if(mLastError & 0xF0)
				r = ("Err: PIN is wrong!");
			else
				r = ("Err: unknown error occured!");
		}
        break;
	}

    return r;   
}


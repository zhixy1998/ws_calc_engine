"use client";

import React from "react";
import { Form, Input, Button, message } from "antd";
import { useRouter } from "next/navigation";
import api from "@/utils/axios";
import Link from "next/link";
// import { toast } from "sonner";

const LoginForm: React.FC = () => {
  const router = useRouter();

  const onFinish = async (values: any) => {
    const loginUrl = `${process.env.NEXT_PUBLIC_API_URL}/user_manage/verify`;
    try {
      const res = await api.post(loginUrl, values);
      const code = res.data.code;
      const token = res.data.token;
      if (code === 200) {
        localStorage.setItem("user_manage_token", token);
        router.push("/");
      } else {
        message.error(res.data.message || "登录失败");
        // toast(res.data.message || "登录失败");
      }
    } catch (err) {
      message.error("网络错误");
    }
  };

  return (
    <Form
      name="login"
      onFinish={onFinish}
      layout="vertical"
      className="space-y-4"
    >
      <Form.Item
        label="密码"
        name="password"
        rules={[{ required: true, message: "请输入密码" }]}
      >
        <Input.Password placeholder="密码" />
      </Form.Item>
      <Form.Item>
        <Button type="primary" htmlType="submit" block>
          登录
        </Button>
      </Form.Item>
    </Form>
  );
};

const Login = () => {
  return (
    // items-center 垂直方向居中
    // justify-center 水平方向居中
    // h-screen 视口高度占满整个屏幕100vh
    // flex-col 让子元素垂直排列
    <div className="flex items-center justify-center h-screen bg-gray-100 flex-col">
      {/* // flex flex-col 内部元素垂直排列 // w-full max-w-md → 宽度
      100%，但最大不超过 md(28rem ≈ 448px) // px-8 pt-6 pb-2 → 内边距 左右各
      2rem(32px)，上 1.5rem(24px)，下 0.5rem(8px) // bg-white → 背景白色 //
      rounded-lg → 大圆角 // shadow-md → 中等阴影 */}
      <div className="flex flex-col w-full max-w-md px-8 pt-6 pb-2 bg-white rounded-lg shadow-md">
        <h1 className="text-center text-4xl pb-4">用户管理</h1>
        <LoginForm />
      </div>
    </div>
  );
};

export default Login;

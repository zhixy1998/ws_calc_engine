import api from "@/utils/axios";
import { use, useEffect, useCallback } from "react";

import React, { useState } from "react";
import { Flex, Space, Table, Tag, Form, Button } from "antd";
import styles from "./user_manage_info.module.scss";
import type { TableProps } from "antd";
import { MenuFoldOutlined, MenuUnfoldOutlined } from "@ant-design/icons";
import { Modal, Input, message } from "antd";

interface DataType {
  key: string;
  name: string;
  password: number;
  login_time: string;
  status: string;
  allowed_time?: string;
  operation: string[];
}

interface OptionType {
  label: React.ReactNode;
  key: string;
  value: number;
}

const statusOptions: OptionType[] = [
  {
    label: <Tag color="blue">全部</Tag>,
    key: "all",
    value: -1,
  },
  {
    label: <Tag color="green">未删除</Tag>,
    key: "active",
    value: 1,
  },
  {
    label: <Tag color="red">已删除</Tag>,
    key: "deleted",
    value: 0,
  },
];

const UserManageInfo: React.FC = () => {
  const [userData, setUserData] = useState([]);
  const urlInfoListUrl = `${process.env.NEXT_PUBLIC_API_URL}/user_manage/users`;

  const [filters, setFilters] = useState<{ status: number }>({ status: -1 });

  const handleValuesChange = useCallback(
    (changedValues: any, allValues: any) => {
      setFilters(allValues);
    },
    []
  );

  const [reloadFlag, setReloadFlag] = useState(false); // 添加一个状态变量作为依赖

  useEffect(() => {
    const params = Object.entries(filters)
      .map(
        ([key, value]) =>
          `${encodeURIComponent(key)}=${encodeURIComponent(value)}`
      )
      .join("&");

    const urlWithParams = `${urlInfoListUrl}?${params}`;

    api.get(urlWithParams).then((response) => {
      if (response.data.code === 200) {
        setUserData(response.data.user_infos || []);
      }
    });
  }, [urlInfoListUrl, filters, reloadFlag]); // 将 reloadFlag 添加为依赖

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [use_time, setUseTime] = useState("");

  const handleCreateAccount = async () => {
    try {
      // 调用接口，url 由用户自行填写
      const urlCreateUrl = `${process.env.NEXT_PUBLIC_API_URL}/user_manage/create_user`;
      api
        .post(urlCreateUrl, { username, password, use_time })
        .then((response) => {
          if (response.data.code === 200) {
            message.success("账号创建成功！");
            setReloadFlag((prev) => !prev); // 切换 reloadFlag 状态以触发 useEffect
          } else if (response.data.code > 500) {
            message.error(response.data.message);
          } else {
            message.error("账号创建失败，请重试！");
          }
        });

      setIsModalOpen(false);
      setUsername("");
      setPassword("");
    } catch (error) {
      message.error("账号创建失败，请重试！");
    }
  };

  const handleDelete = async (userId: string) => {
    try {
      const deleteUrl = `${process.env.NEXT_PUBLIC_API_URL}/user_manage/delete_user`;
      const response = await api.post(deleteUrl, { user_id: userId });
      if (response.data.code === 200) {
        message.success("删除成功！");
        setReloadFlag((prev) => !prev); // 切换 reloadFlag 状态以触发 useEffect
      } else {
        message.error("删除失败，请重试！");
      }
    } catch (error) {
      message.error("删除失败，请重试！");
    }
  };

  const columns: TableProps<DataType>["columns"] = [
    {
      title: "用户名",
      dataIndex: "name",
      key: "name",
      render: (text) => <a>{text}</a>,
    },
    {
      title: "密码",
      dataIndex: "password",
      key: "password",
    },
    {
      title: "登录时间",
      dataIndex: "login_time",
      key: "login_time",
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (text) =>
        text == "1" ? (
          <Tag color="green">未删除</Tag>
        ) : (
          <Tag color="red">已删除</Tag>
        ),
    },
    {
      title: "允许使用时间",
      dataIndex: "allowed_time",
      key: "allowed_time",
    },

    {
      title: "操作",
      key: "operation",
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="primary"
            danger
            onClick={() => handleDelete(record.key)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const generateOptions = (options: OptionType[]) => {
    return (
      options?.filter(Boolean).map((option) => {
        return (
          <option key={option.key} value={option.value}>
            {option.label}
          </option>
        );
      }) || []
    );
  };

  return (
    <div className="flex flex-row h-full mt-2 mr-2 ">
      <div className="w-[10%] border-l border-gray-500 bg-gray-200">
        <h2 className="my-2 text-lg font-semibold text-center">筛选</h2>
        <div className="bg-white rounded-lg m-2 p-2 h-full">
          <Form layout="vertical" onValuesChange={handleValuesChange}>
            <Form.Item label="状态" name="status" className="text-blue-400">
              <select className="w-full border border-gray-300 rounded px-2 py-1">
                {generateOptions(statusOptions)}
              </select>
            </Form.Item>
            {/* <Form.Item label="使用时间" name="time" className="text-blue-400">
              <select className="w-full border border-gray-300 rounded px-2 py-1">
                <option value="all">全部</option>
                <option value="within_limit">未删除</option>
                <option value="exceeded">删除</option>
              </select>
            </Form.Item> */}
          </Form>
        </div>
      </div>
      <div className="w-[90%] ml-2 h-full flex flex-col">
        {/* 让表格容器伸展并可滚动 */}
        <div className="flex-1 overflow-hidden">
          <div className={styles.customTable}>
            <Table<DataType>
              columns={columns}
              dataSource={userData}
              pagination={{ pageSize: 20 }}
              className={styles.tableWrapper}
              scroll={{ y: "calc(100vh - 100px)" }}
            />
          </div>
        </div>
      </div>
      <div className="w-[10%] border-l border-gray-500 bg-gray-200 flex flex-col items-center">
        <Button
          className="flex bg-yellow-400"
          onClick={() => setIsModalOpen(true)}
        >
          创建账号
        </Button>
      </div>

      <Modal
        title="创建账号"
        open={isModalOpen}
        onOk={handleCreateAccount}
        onCancel={() => setIsModalOpen(false)}
        okText="确定"
        cancelText="取消"
      >
        <div className="flex flex-col gap-4">
          <Input
            placeholder="请输入账号"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <Input.Password
            placeholder="请输入密码"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Input
            placeholder="账号使用时间(分钟, 默认60分钟)"
            value={use_time}
            onChange={(e) => setUseTime(e.target.value)}
          />
        </div>
      </Modal>
    </div>
  );
};

export default UserManageInfo;

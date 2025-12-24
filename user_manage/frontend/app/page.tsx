"use client";
import UserManageInfo from "@/components/t_800/user_manage_info";

const HomePage = () => {
  return (
    <div className="flex flex-col h-[100vh]">
      <h1 className="text-center my-4 text-3xl">T800临时用户管理系统</h1>

      <div className="flex flex-1">
        {/* 使用 flex-1 让中间部分占满剩余空间 */}

        <div className="bg-gray-200 h-[100vh] overflow-auto">
          <UserManageInfo />
        </div>
      </div>
    </div>
  );
};

export default HomePage;

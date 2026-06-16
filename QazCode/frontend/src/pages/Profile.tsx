import React from 'react';

export default function Profile() {
  const handleLogout = () => {
    localStorage.removeItem('token');
    window.location.href = '/login';
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-50">
      <div className="bg-white p-8 rounded-lg shadow border text-center w-96">
        <h2 className="text-2xl font-bold mb-4">User Profile</h2>
        <p className="text-gray-600 mb-8">More profile details can go here later!</p>
        
        <button 
          onClick={handleLogout}
          className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 w-full"
        >
          Logout
        </button>
        <button 
          onClick={() => window.location.href = '/'}
          className="mt-4 text-blue-500 hover:underline"
        >
          Back to Chat
        </button>
      </div>
    </div>
  );
}
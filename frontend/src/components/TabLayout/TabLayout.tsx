import { FC } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Tabbar } from '@telegram-apps/telegram-ui';

import './TabLayout.css';

const TABS = [
  {
    path: '/markets',
    text: 'Рынки',
    icon: (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 21V11h4v10H4ZM12 21V7h4v14h-4ZM20 21V3h4v18h-4Z" fill="currentColor"/>
      </svg>
    ),
  },
  {
    path: '/portfolio',
    text: 'Портфель',
    icon: (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M5 9a2 2 0 0 1 2-2h2V5a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v2h2a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V9Zm6-2h6V5h-6v2Z" fill="currentColor"/>
      </svg>
    ),
  },
  {
    path: '/profile',
    text: 'Профиль',
    icon: (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M14 4a5 5 0 1 1 0 10 5 5 0 0 1 0-10ZM6 22c0-3.3 2.7-6 6-6h4c3.3 0 6 2.7 6 6v1H6v-1Z" fill="currentColor"/>
      </svg>
    ),
  },
];

export const TabLayout: FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <div className="tab-layout">
      <div className="tab-layout__content">
        <Outlet />
      </div>
      <Tabbar className="tab-layout__tabbar">
        {TABS.map((tab) => (
          <Tabbar.Item
            key={tab.path}
            text={tab.text}
            selected={location.pathname === tab.path}
            onClick={() => navigate(tab.path)}
          >
            {tab.icon}
          </Tabbar.Item>
        ))}
      </Tabbar>
    </div>
  );
};

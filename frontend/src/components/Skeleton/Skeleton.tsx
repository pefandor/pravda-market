import type { FC, CSSProperties } from 'react';
import './Skeleton.css';

interface SkeletonProps {
  width?: string;
  height?: string;
  borderRadius?: string;
  style?: CSSProperties;
}

export const Skeleton: FC<SkeletonProps> = ({
  width = '100%',
  height = '16px',
  borderRadius,
  style,
}) => (
  <div
    className="skeleton"
    style={{
      width,
      height,
      borderRadius: borderRadius ?? undefined,
      ...style,
    }}
  />
);

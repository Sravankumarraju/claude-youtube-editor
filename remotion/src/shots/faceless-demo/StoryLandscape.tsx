import React from 'react';
import { StoryboardVideo } from '../../lib/storyboard';
import { DEMO_SCENES } from './demoScenes';

export const compositionConfig = { id: 'StoryLandscape', durationInSeconds: 30, fps: 30, width: 1920, height: 1080 };

const StoryLandscape: React.FC = () => (
  <StoryboardVideo scenes={DEMO_SCENES} width={1920} height={1080} captions />
);
export default StoryLandscape;

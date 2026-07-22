import React from 'react';
import { StoryboardVideo } from '../../lib/storyboard';
import { DEMO_SCENES } from './demoScenes';

export const compositionConfig = { id: 'StoryVertical', durationInSeconds: 30, fps: 30, width: 1080, height: 1920 };

const StoryVertical: React.FC = () => (
  <StoryboardVideo scenes={DEMO_SCENES} width={1080} height={1920} captions />
);
export default StoryVertical;

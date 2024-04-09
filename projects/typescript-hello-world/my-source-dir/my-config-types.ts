// Matches structure of config.yaml
export interface BlockTwoConfig {
  var4: string;
}

export interface ConfigData {
    block1: {
        var1: string;
        var2: string[];
    }
    var3?: string; // Optional variable
    secondBlock: BlockTwoConfig;
}

export const defaultBlockTwoConfig: BlockTwoConfig = {
  var4: 'defaultVar4', // Default value for var4
}

// Set default values for ConfigData
export const defaultConfigData: ConfigData = {
  block1: {
    var1: 'defaultVar1',
    var2: ['defaultItem1', 'defaultItem2'],
  },
  var3: 'let you down', // Default value for var3
  secondBlock: { ...defaultBlockTwoConfig },
};
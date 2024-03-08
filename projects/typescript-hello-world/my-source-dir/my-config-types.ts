// Matches structure of config.yaml
export interface ConfigData {
    block1: {
        var1: string;
        var2: string[];
    }
    var3?: string; // Optional variable
}


// Set default values for ConfigData
export const defaultConfigData: ConfigData = {
  block1: {
    var1: 'defaultVar1',
    var2: ['defaultItem1', 'defaultItem2'],
  },
  var3: 'let you down', // Default value for var3
};
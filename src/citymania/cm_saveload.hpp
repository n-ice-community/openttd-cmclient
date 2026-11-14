#ifndef CITYMANIA_SAVELOAD_HPP
#define CITYMANIA_SAVELOAD_HPP

#include "../saveload/saveload.h"
#include "../town.h"

namespace citymania {

class SlTownGrowthTiles : public DefaultSaveLoadHandler<SlTownGrowthTiles, Town> {
public:
    inline static const SaveLoad description[] = {
        SaveLoad::Variable<VarFileType::U32>("tile", SLE_OBJECT_ADDRESS(TownsGrowthTilesIndex::value_type, first), SaveLoadVersion::TableChunks),
        SaveLoad::Variable<VarFileType::U8>("state", SLE_OBJECT_ADDRESS(TownsGrowthTilesIndex::value_type, second), SaveLoadVersion::TableChunks),
    };
    inline const static SaveLoadCompatTable compat_description;

    void Save(Town *t) const override;
    void Load(Town *t) const override;
};

class SlTownGrowthTilesLastMonth : public DefaultSaveLoadHandler<SlTownGrowthTilesLastMonth, Town> {
public:
    inline static const SaveLoad description[] = {
        SaveLoad::Variable<VarFileType::U32>("tile", SLE_OBJECT_ADDRESS(TownsGrowthTilesIndex::value_type, first), SaveLoadVersion::TableChunks),
        SaveLoad::Variable<VarFileType::U8>("state", SLE_OBJECT_ADDRESS(TownsGrowthTilesIndex::value_type, second), SaveLoadVersion::TableChunks),
    };
    inline const static SaveLoadCompatTable compat_description;

    void Save(Town *t) const override;
    void Load(Town *t) const override;
};

}  // namespace citymania
#endif

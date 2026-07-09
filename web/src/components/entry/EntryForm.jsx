import React, { useState, useEffect } from 'react';
import { Card, Form, Input, Select, Radio, DatePicker, Button, Checkbox, InputNumber, Space, message, Divider, Collapse, Row, Col, Typography, Modal } from 'antd';
import { SaveOutlined, DownloadOutlined, UserOutlined, HomeOutlined, MailOutlined, GlobalOutlined, PlusOutlined } from '@ant-design/icons';
import moment from 'moment';
import { getFormOptions, addFormOption, saveCase, downloadExcel, sendEmail, submitWeb } from '../../api/entry';
import { getOrganizations, createOrganization } from '../../api/organizations';

const { Option } = Select;
const { TextArea } = Input;
const { Title } = Typography;

const branchOptions = ["cn Đà Nẵng", "cn Miền Bắc", "CN Miền Nam"];
const officeMapping = {
  "cn Đà Nẵng": ["vp Đà Nẵng"],
  "cn Miền Bắc": ["vp Hưng Yên", "vp Hải Phòng", "vp Hà Nam Ninh", "vp Hà Nội", "vp Nghệ An", "vp Thái Nguyên"],
  "CN Miền Nam": ["vp Cần Thơ", "vp HCM", "vp Đồng Nai", "vp Bình Dương"]
};

const formatContractNumber = (value) => {
  if (!value) return value;
  const val = value.trim();
  const currentYear = new Date().getFullYear();
  const currentMonth = String(new Date().getMonth() + 1).padStart(2, '0');
  
  if (/^\d{4}$/.test(val)) {
    return `010/${currentYear}/N${currentMonth}-${val}/DN`;
  }
  if (/^\.\d{4}$/.test(val)) {
    return `010/${currentYear}/N${currentMonth}.${val.substring(1)}/DN`;
  }
  return value;
};

// Cascading locations mock data
const locationsData = {
  "Gia Lai": {
    "Pleiku": ["Hoa Lư", "Phù Đổng", "Tây Sơn"],
    "An Khê": ["An Bình", "An Phú", "An Tân"]
  },
  "Đà Nẵng": {
    "Thanh Khê": ["An Khê", "Hòa Khê", "Chính Gián"],
    "Hải Châu": ["Thạch Thang", "Thuận Phước", "Hòa Cường Bắc"]
  },
  "Hồ Chí Minh": {
    "Quận 1": ["Bến Nghé", "Bến Thành", "Đa Kao"],
    "Bình Thạnh": ["Phường 15", "Phường 25", "Phường 27"]
  }
};

const readExtractedValue = (field) => field?.value || '';

const buildOcrPersonalNote = (formValues) => {
  const notes = Array.isArray(formValues?.notes) ? [...formValues.notes] : [];
  [
    ['Số giấy chứng nhận', formValues?.so_giay_chung_nhan],
    ['Số vào sổ cấp giấy chứng nhận', formValues?.so_vao_so_cap_giay_chung_nhan],
    ['Ngày cấp giấy chứng nhận', formValues?.ngay_cap_giay_chung_nhan],
  ].forEach(([label, field]) => {
    const value = readExtractedValue(field).trim();
    const note = value ? `${label}: ${value}` : '';
    if (note && !notes.includes(note)) notes.push(note);
  });
  return notes.join('\n');
};

export default function EntryForm({ uploadId, formValues, onSaveSuccess }) {
  const [form] = Form.useForm();
  const [formOptions, setFormOptions] = useState({});
  const [organizations, setOrganizations] = useState([]);
  const [loadingOptions, setLoadingOptions] = useState(false);
  const [saving, setSaving] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [sendingEmail, setSendingEmail] = useState(false);
  const [submittingWeb, setSubmittingWeb] = useState(false);
  
  const [customPurposes, setCustomPurposes] = useState([]);
  const [customSources, setCustomSources] = useState([]);
  const [customStaffs, setCustomStaffs] = useState([]);

  const [newOrgModalOpen, setNewOrgModalOpen] = useState(false);
  const [newOrgForm] = Form.useForm();

  const saveCustomOption = async (field, value, setCustomOptions) => {
    await addFormOption(field, value);
    setFormOptions(prev => ({
      ...prev,
      [field]: [...new Set([...(prev[field] || []), value])],
    }));
    setCustomOptions([]);
  };

  const handleCreateOrgSubmit = async (values) => {
    try {
      const res = await createOrganization({
        name: values.name.trim(),
        address: values.address || '',
        tax_code: values.tax_code || '',
        representative: values.representative || '',
        position: values.position || '',
      });
      message.success('Thêm tổ chức mới thành công! 🏢');
      setNewOrgModalOpen(false);
      newOrgForm.resetFields();
      
      // Reload organizations list
      const newOrgsRes = await getOrganizations();
      const newOrgs = newOrgsRes.data || [];
      setOrganizations(newOrgs);
      
      // Auto select and fill in the form
      form.setFieldsValue({
        entry_org_searchbox: res.data.id,
        customer_info: values.name.trim(),
        customer_address: values.address || '',
        tax_code: values.tax_code || '',
        representative_name: values.representative || '',
        representative_position: values.position || '',
      });
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Thêm tổ chức thất bại');
    }
  };

  const handleAddNewPurpose = () => {
    let inputVal = '';
    Modal.confirm({
      title: 'Thêm mới Mục đích thẩm định',
      icon: <PlusOutlined style={{ color: '#007f7a' }} />,
      content: (
        <Input 
          placeholder="Nhập mục đích mới..." 
          onChange={(e) => { inputVal = e.target.value; }} 
          style={{ marginTop: 12 }}
        />
      ),
      okText: 'Thêm',
      cancelText: 'Hủy',
    onOk: async () => {
      const val = inputVal.trim();
      if (val) {
        try {
          await saveCustomOption('valuation_purpose', val, setCustomPurposes);
          form.setFieldValue('valuation_purpose', val);
          message.success('Đã lưu mục đích thẩm định mới');
        } catch (err) {
          message.error(err.response?.data?.error || 'Không lưu được mục đích thẩm định mới');
          throw err;
        }
      }
    }
  });
};

  const handleAddNewSource = () => {
    let inputVal = '';
    Modal.confirm({
      title: 'Thêm mới Nguồn / Ngân hàng',
      icon: <PlusOutlined style={{ color: '#007f7a' }} />,
      content: (
        <Input 
          placeholder="Nhập nguồn/ngân hàng mới..." 
          onChange={(e) => { inputVal = e.target.value; }} 
          style={{ marginTop: 12 }}
        />
      ),
      okText: 'Thêm',
      cancelText: 'Hủy',
    onOk: async () => {
      const val = inputVal.trim();
      if (val) {
        try {
          await saveCustomOption('source', val, setCustomSources);
          form.setFieldValue('source', val);
          message.success('Đã lưu nguồn/ngân hàng mới');
        } catch (err) {
          message.error(err.response?.data?.error || 'Không lưu được nguồn/ngân hàng mới');
          throw err;
        }
      }
    }
  });
};

  const handleAddNewStaff = () => {
    let inputVal = '';
    Modal.confirm({
      title: 'Thêm mới Chuyên viên nghiệp vụ',
      icon: <PlusOutlined style={{ color: '#007f7a' }} />,
      content: (
        <Input 
          placeholder="Nhập tên chuyên viên mới..." 
          onChange={(e) => { inputVal = e.target.value; }} 
          style={{ marginTop: 12 }}
        />
      ),
      okText: 'Thêm',
      cancelText: 'Hủy',
    onOk: async () => {
      const val = inputVal.trim();
      if (val) {
        try {
          await saveCustomOption('valuation_staff', val, setCustomStaffs);
          form.setFieldValue('valuation_staff', val);
          message.success('Đã lưu nhân sự thẩm định mới');
        } catch (err) {
          message.error(err.response?.data?.error || 'Không lưu được nhân sự thẩm định mới');
          throw err;
        }
      }
    }
  });
};
  
  // Dynamic form state
  const [customerType, setCustomerType] = useState('individual');
  const [selectedBranch, setSelectedBranch] = useState('cn Đà Nẵng');
  const [offices, setOffices] = useState(["vp Đà Nẵng"]);
  
  // Cascading location state
  const [provinces, setProvinces] = useState(Object.keys(locationsData));
  const [districts, setDistricts] = useState([]);
  const [wards, setWards] = useState([]);
  
  const [selectedProvince, setSelectedProvince] = useState(null);
  const [selectedDistrict, setSelectedDistrict] = useState(null);

  const fetchOrganizations = async () => {
    try {
      const res = await getOrganizations();
      setOrganizations(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchFormOptions();
    fetchOrganizations();
  }, []);

  useEffect(() => {
    if (formValues) {
      // Pre-fill form from OCR trích xuất
      form.setFieldsValue({
        so_thua_dat: formValues.so_thua_dat?.value || formValues.so_thua || '',
        so_to_ban_do: formValues.so_to_ban_do?.value || formValues.so_to || '',
        dia_chi_thua_dat: formValues.dia_chi_thua_dat?.value || formValues.land_address || '',
        owner_name: formValues.ten_chu_so_huu_cuoi_cung?.value || formValues.owner_name || '',
        owner_address: formValues.dia_chi_chu_so_huu_cuoi_cung?.value || formValues.owner_address || '',
        citizen_id: formValues.so_cccd_chu_so_huu_cuoi_cung?.value || formValues.so_cccd || '',
        
        // Populate standard form fields
        customer_info: formValues.ten_chu_so_huu_cuoi_cung?.value || formValues.owner_name || '',
        customer_address: formValues.dia_chi_chu_so_huu_cuoi_cung?.value || formValues.owner_address || '',
        asset_description: formValues.asset_description || (formValues.so_thua_dat?.value || formValues.so_thua 
          ? `Thửa đất số ${formValues.so_thua_dat?.value || formValues.so_thua}, tờ bản đồ số ${formValues.so_to_ban_do?.value || formValues.so_to || ''}; tại địa chỉ ${formValues.dia_chi_thua_dat?.value || formValues.land_address || ''}` 
          : ''),
        personal_note: buildOcrPersonalNote(formValues)
      });
      
      // Auto guess locations if available
      guessLocationFromAddress(formValues.dia_chi_thua_dat?.value || '');
    }
  }, [formValues, form]);

  const fetchFormOptions = async () => {
    setLoadingOptions(true);
    try {
      const res = await getFormOptions();
      setFormOptions(res.data || {});
    } catch (err) {
      console.error(err);
      message.error('Không thể tải dropdown options từ Excel template');
    } finally {
      setLoadingOptions(false);
    }
  };

  const guessLocationFromAddress = (address) => {
    if (!address) return;
    const addr = address.toLowerCase();
    let matchedProvince = null;
    
    for (const prov of Object.keys(locationsData)) {
      if (addr.includes(prov.toLowerCase())) {
        matchedProvince = prov;
        break;
      }
    }
    
    if (matchedProvince) {
      form.setFieldValue('province', matchedProvince);
      handleProvinceChange(matchedProvince);
      
      // Try district
      let matchedDistrict = null;
      for (const dist of Object.keys(locationsData[matchedProvince])) {
        if (addr.includes(dist.toLowerCase())) {
          matchedDistrict = dist;
          break;
        }
      }
      
      if (matchedDistrict) {
        form.setFieldValue('district', matchedDistrict);
        handleDistrictChange(matchedDistrict, matchedProvince);
        
        // Try ward
        let matchedWard = null;
        for (const ward of locationsData[matchedProvince][matchedDistrict]) {
          if (addr.includes(ward.toLowerCase())) {
            matchedWard = ward;
            break;
          }
        }
        if (matchedWard) {
          form.setFieldValue('ward', matchedWard);
        }
      }
    }
  };

  const handleProvinceChange = (value) => {
    setSelectedProvince(value);
    setSelectedDistrict(null);
    setDistricts(Object.keys(locationsData[value] || {}));
    setWards([]);
    form.setFieldsValue({ district: undefined, ward: undefined });
  };

  const handleDistrictChange = (value, prov = selectedProvince) => {
    setSelectedDistrict(value);
    setWards(locationsData[prov]?.[value] || []);
    form.setFieldsValue({ ward: undefined });
  };

  const handleBranchChange = (value) => {
    setSelectedBranch(value);
    const newOffices = officeMapping[value] || [];
    setOffices(newOffices);
    form.setFieldsValue({ office: newOffices[0] });
  };

  const handleCustomerTypeChange = (e) => {
    const val = e.target.value;
    setCustomerType(val);
  };

  const handleOrgSelect = (value) => {
    if (value === '__new__') {
      form.setFieldsValue({
        customer_info: '',
        customer_address: '',
        tax_code: '',
        representative_name: '',
        representative_position: '',
      });
      return;
    }
    const org = organizations.find(o => o.id === value);
    if (org) {
      form.setFieldsValue({
        customer_info: org.name || '',
        customer_address: org.address || '',
        tax_code: org.tax_code || '',
        representative_name: org.representative || '',
        representative_position: org.position || '',
      });
    }
  };

  const formatPayload = (values) => {
    // Format Month
    const executionMonth = values.execution_month 
      ? values.execution_month.format('MM/YYYY') 
      : moment().format('MM/YYYY');
      
    // Format Date
    const contractDate = values.contract_date 
      ? values.contract_date.format('DD/MM/YYYY') 
      : moment().format('DD/MM/YYYY');

    // Build values dict
    return {
      customer_type: customerType,
      case_status: values.case_status || 'Đang xử lý',
      execution_month: executionMonth,
      payment_status: values.payment_status || 'Chưa thanh toán',
      contract_number: values.contract_number,
      contract_date: contractDate,
      asset_type: values.asset_type,
      asset_description: values.asset_description,
      preliminary_status: values.preliminary_status,
      valuation_purpose: values.valuation_purpose,
      valuation_branch: selectedBranch,
      office: values.office,
      source: values.source,
      
      // Customer Details
      customer_info: values.customer_info,
      customer_phone: values.customer_phone || '',
      customer_address: values.customer_address,
      citizen_id: values.citizen_id || '',
      
      // Fees
      valuation_fee_number: values.valuation_fee_number || 0,
      advance_payment: values.advance_payment ? String(values.advance_payment) : '0',
      valuation_staff: values.valuation_staff,
      personal_note: values.personal_note || '',
      
      // GCN details
      so_thua_dat: values.so_thua_dat || '',
      so_to_ban_do: values.so_to_ban_do || '',
      dia_chi_thua_dat: values.dia_chi_thua_dat || '',
      owner_name: values.owner_name || '',
      owner_address: values.owner_address || '',
      owner_citizen_id: values.citizen_id || '',
      
      // Organization fields (optional)
      tax_code: values.tax_code || '',
      representative_name: values.representative_name || '',
      representative_position: values.representative_position || '',
      authorization_note: values.authorization_note || '',
      handover_contact_name: values.handover_contact_name || '',
      handover_contact_position: values.handover_contact_position || '',
      handover_contact_phone: values.handover_contact_phone || '',

      // Province/District/Ward selections
      province: values.province || '',
      district: values.district || '',
      ward: values.ward || ''
    };
  };

  const handleSave = async (values) => {
    setSaving(true);
    try {
      const payload = formatPayload(values);
      const res = await saveCase({
        extraction: payload,
        case_type: customerType,
        upload_id: uploadId
      });
      message.success('Lưu hồ sơ thành công! 💾');
      if (onSaveSuccess) onSaveSuccess(res.data?.case_id);
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Lưu hồ sơ thất bại');
    } finally {
      setSaving(false);
    }
  };

  const handleDownloadExcel = async () => {
    try {
      const values = await form.validateFields();
      setDownloading(true);
      const payload = formatPayload(values);
      
      const response = await downloadExcel(payload);
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `filled_GCN_${payload.contract_number || 'export'}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      message.success('Tải file Excel nhập liệu thành công! 📊');
    } catch (err) {
      console.error(err);
      message.error('Vui lòng điền các trường bắt buộc trước khi xuất Excel');
    } finally {
      setDownloading(false);
    }
  };

  const handleSendEmail = async () => {
    try {
      const values = await form.validateFields();
      setSendingEmail(true);
      const payload = formatPayload(values);
      
      const isForwardEnabled = form.getFieldValue('professional_forward_enabled');
      payload.professional_forward_enabled = isForwardEnabled ? '1' : '0';
      payload.professional_recipient_email = isForwardEnabled ? form.getFieldValue('professional_recipient_email') : '';

      const res = await sendEmail(payload);
      message.success(`Đã gửi mail yêu cầu định giá tới ${res.data?.to_email || 'người nhận'}.`);
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Gửi mail thất bại');
    } finally {
      setSendingEmail(false);
    }
  };

  const handleSubmitWeb = async () => {
    try {
      const values = await form.validateFields();
      setSubmittingWeb(true);
      const payload = formatPayload(values);
      
      const res = await submitWeb(payload);
      message.success(res.data?.message || 'Gửi Web thành công! 🌐');
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Gửi Web thất bại');
    } finally {
      setSubmittingWeb(false);
    }
  };

  return (
    <Card 
      style={{ borderRadius: 12, border: '1px solid #d8e7e5' }}
      bodyStyle={{ padding: '16px 20px' }}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSave}
        initialValues={{
          payment_status: 'Chưa thanh toán',
          case_status: 'Đang xử lý',
          execution_month: moment(),
          contract_date: moment(),
          advance_payment: 0,
          valuation_fee_number: 0,
          asset_type: 'BĐS đặc thù khác',
          professional_forward_enabled: true,
          professional_recipient_email: 'Kietna@cenvalue.vn'
        }}
        style={{ display: 'flex', flexDirection: 'column' }}
      >
        <div style={{ paddingBottom: 20, overflow: 'visible' }}>
          {/* Section 1: Customer & Contract details (without title) */}
          <div style={{ display: 'flex', gap: 16, marginBottom: 12 }}>
            <Form.Item label="Loại khách hàng" style={{ marginBottom: 0, flex: 1 }}>
              <Radio.Group onChange={handleCustomerTypeChange} value={customerType}>
                <Radio value="individual">Cá nhân</Radio>
                <Radio value="organization">Tổ chức</Radio>
              </Radio.Group>
            </Form.Item>
            
            <Form.Item name="case_status" label="Trạng thái hồ sơ" style={{ marginBottom: 0, flex: 1 }}>
              <Select placeholder="Chọn trạng thái...">
                <Option value="Đang xử lý">Đang xử lý</Option>
                <Option value="Hoàn thành">Hoàn thành</Option>
                <Option value="Hủy">Hủy</Option>
              </Select>
            </Form.Item>
          </div>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="contract_number"
                label="Số hợp đồng"
                rules={[{ required: true, message: 'Vui lòng nhập số hợp đồng' }]}
              >
                <Input 
                  placeholder="010-2026/CENVALUE-GL" 
                  onBlur={(e) => {
                    const formatted = formatContractNumber(e.target.value);
                    form.setFieldsValue({ contract_number: formatted });
                  }}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="contract_date" label="Ngày hợp đồng">
                <DatePicker format="DD/MM/YYYY" style={{ width: '100%' }} placeholder="VD: 06/10/2025" />
              </Form.Item>
            </Col>
          </Row>

          {customerType === 'organization' && (
            <Row gutter={16}>
              <Col span={24}>
                <Form.Item
                  label="Tìm kiếm từ danh bạ (Mã số thuế / Tên)"
                  name="entry_org_searchbox"
                >
                  <Select
                    showSearch
                    placeholder="-- Chọn từ danh bạ hoặc nhập mới --"
                    optionFilterProp="label"
                    onChange={handleOrgSelect}
                    defaultValue="__new__"
                    dropdownRender={(menu) => (
                      <>
                        {menu}
                        <Divider style={{ margin: '4px 0' }} />
                        <div style={{ padding: '4px 8px', textAlign: 'center' }}>
                          <Button 
                            type="text" 
                            size="small" 
                            icon={<PlusOutlined />} 
                            style={{ width: '100%', color: '#007f7a', fontWeight: 600 }}
                            onClick={() => setNewOrgModalOpen(true)}
                          >
                            Thêm mới tổ chức...
                          </Button>
                        </div>
                      </>
                    )}
                    options={[
                      { value: '__new__', label: '-- Chọn từ danh bạ hoặc nhập mới --' },
                      ...organizations.map(o => ({
                        value: o.id,
                        label: `${o.name} (${o.tax_code || ''})`
                      }))
                    ]}
                  />
                </Form.Item>
              </Col>
            </Row>
          )}

          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="customer_info"
                label={customerType === 'individual' ? 'Tên khách hàng' : 'Tên công ty / tổ chức'}
                rules={[{ required: true, message: 'Vui lòng nhập tên khách hàng' }]}
              >
                <Input placeholder={customerType === 'individual' ? 'Nguyễn Văn A' : 'Công ty TNHH A'} />
              </Form.Item>
            </Col>
          </Row>

          {customerType === 'individual' ? (
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item
                  name="customer_address"
                  label="Địa chỉ khách hàng"
                  rules={[{ required: true, message: 'Vui lòng nhập địa chỉ' }]}
                >
                  <Input placeholder="Nhập địa chỉ..." />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="citizen_id" label="Số CCCD/CMND">
                  <Input placeholder="Nhập số CCCD..." />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="customer_phone" label="Số điện thoại">
                  <Input placeholder="090..." />
                </Form.Item>
              </Col>
            </Row>
          ) : (
            <>
              <Row gutter={16}>
                <Col span={24}>
                  <Form.Item
                    name="customer_address"
                    label="Địa chỉ công ty"
                    rules={[{ required: true, message: 'Vui lòng nhập địa chỉ công ty' }]}
                  >
                    <Input placeholder="Nhập địa chỉ..." />
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item name="tax_code" label="Mã số thuế">
                    <Input placeholder="MST..." />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="representative_name" label="Người đại diện pháp luật">
                    <Input placeholder="Họ tên người đại diện..." />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="representative_position" label="Chức vụ người đại diện">
                    <Input placeholder="Giám đốc, Chủ tịch..." />
                  </Form.Item>
                </Col>
              </Row>
            </>
          )}

          {/* Section 2: Thông tin Nghiệp vụ */}
          <Title level={4} style={{ marginTop: 20, marginBottom: 12 }}>Thông tin Nghiệp vụ</Title>

          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="asset_description"
                label="Tài sản thẩm định giá"
                rules={[{ required: true, message: 'Vui lòng nhập mô tả tài sản' }]}
              >
                <TextArea rows={3} placeholder="Vd: 43,12, Tổ 2 An Tân, phường An Khê, tỉnh Gia Lai" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="asset_type" label="Loại tài sản">
                <Select placeholder="Chọn loại..." loading={loadingOptions}>
                  {(formOptions.asset_type || []).map(t => <Option key={t} value={t}>{t}</Option>)}
                </Select>
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="preliminary_status" label="Sơ bộ">
                <Select placeholder="Chọn trạng thái sơ bộ..." loading={loadingOptions}>
                  {(formOptions.preliminary_status || []).map(p => <Option key={p} value={p}>{p}</Option>)}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="valuation_purpose" label="Mục đích thẩm định">
                <Select 
                  showSearch 
                  optionFilterProp="children" 
                  placeholder="Chọn mục đích..." 
                  loading={loadingOptions}
                  dropdownRender={(menu) => (
                    <>
                      {menu}
                      <Divider style={{ margin: '4px 0' }} />
                      <div style={{ padding: '4px 8px', textAlign: 'center' }}>
                        <Button 
                          type="text" 
                          size="small" 
                          icon={<PlusOutlined />} 
                          style={{ width: '100%', color: '#007f7a', fontWeight: 600 }}
                          onClick={handleAddNewPurpose}
                        >
                          Thêm mới...
                        </Button>
                      </div>
                    </>
                  )}
                >
                  {[...(formOptions.valuation_purpose || []), ...customPurposes].map(p => <Option key={p} value={p}>{p}</Option>)}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="Chi nhánh thẩm định">
                <Select value={selectedBranch} onChange={handleBranchChange}>
                  {branchOptions.map(b => <Option key={b} value={b}>{b}</Option>)}
                </Select>
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="office" label="Chọn Văn Phòng">
                <Select placeholder="Chọn văn phòng...">
                  {offices.map(o => <Option key={o} value={o}>{o}</Option>)}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="source" label="Nguồn/đối tác">
                <Select 
                  showSearch 
                  optionFilterProp="children" 
                  placeholder="Chọn nguồn..." 
                  loading={loadingOptions}
                  dropdownRender={(menu) => (
                    <>
                      {menu}
                      <Divider style={{ margin: '4px 0' }} />
                      <div style={{ padding: '4px 8px', textAlign: 'center' }}>
                        <Button 
                          type="text" 
                          size="small" 
                          icon={<PlusOutlined />} 
                          style={{ width: '100%', color: '#007f7a', fontWeight: 600 }}
                          onClick={handleAddNewSource}
                        >
                          Thêm mới...
                        </Button>
                      </div>
                    </>
                  )}
                >
                  {[...(formOptions.source || []), ...customSources].map(s => <Option key={s} value={s}>{s}</Option>)}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="valuation_fee_number" label="Phí thẩm định">
                <InputNumber
                  style={{ width: '100%' }}
                  formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={value => value.replace(/\$\s?|(,*)/g, '')}
                  placeholder="0"
                />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="advance_payment" label="Tạm ứng">
                <InputNumber
                  style={{ width: '100%' }}
                  formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={value => value.replace(/\$\s?|(,*)/g, '')}
                  placeholder="0"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="valuation_staff" label="Chuyên viên nghiệp vụ">
                <Select 
                  showSearch
                  optionFilterProp="children"
                  placeholder="Chọn thẩm định viên..." 
                  loading={loadingOptions}
                  dropdownRender={(menu) => (
                    <>
                      {menu}
                      <Divider style={{ margin: '4px 0' }} />
                      <div style={{ padding: '4px 8px', textAlign: 'center' }}>
                        <Button 
                          type="text" 
                          size="small" 
                          icon={<PlusOutlined />} 
                          style={{ width: '100%', color: '#007f7a', fontWeight: 600 }}
                          onClick={handleAddNewStaff}
                        >
                          Thêm mới...
                        </Button>
                      </div>
                    </>
                  )}
                >
                  {[...(formOptions.valuation_staff || []), ...customStaffs].map(staff => <Option key={staff} value={staff}>{staff}</Option>)}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={24}>
              <Form.Item name="personal_note" label="Ghi chú cá nhân">
                <TextArea rows={2} placeholder="Ghi chú nội bộ..." />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={24}>
              <Form.Item name="execution_month" label="Tháng thực hiện" style={{ display: 'none' }}>
                <DatePicker picker="month" format="MM/YYYY" style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="payment_status" label="Thanh toán" style={{ display: 'none' }}>
                <Select>
                  <Option value="Chưa thanh toán">Chưa thanh toán</Option>
                  <Option value="Đã thanh toán">Đã thanh toán</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          {/* Section 3: Collapse for GCN Details */}
          <Collapse ghost style={{ marginBottom: 16, backgroundColor: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0' }}>
            <Collapse.Panel header={<span>📄 Thông tin GCN trích xuất (từ AI)</span>} key="1">
              <Divider style={{ margin: '8px 0' }}>Bản đồ vị trí (Tỉnh/Huyện/Xã)</Divider>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item name="province" label="Tỉnh / Thành phố">
                    <Select placeholder="Chọn Tỉnh..." onChange={handleProvinceChange}>
                      {provinces.map(p => <Option key={p} value={p}>{p}</Option>)}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="district" label="Quận / Huyện">
                    <Select placeholder="Chọn Huyện..." onChange={(val) => handleDistrictChange(val)} disabled={!districts.length}>
                      {districts.map(d => <Option key={d} value={d}>{d}</Option>)}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="ward" label="Phường / Xã">
                    <Select placeholder="Chọn Xã..." disabled={!wards.length}>
                      {wards.map(w => <Option key={w} value={w}>{w}</Option>)}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Divider style={{ margin: '8px 0' }}>Thông tin chi tiết GCN trích xuất</Divider>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="so_thua_dat" label="Số thửa đất">
                    <Input placeholder="Vd: 43" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="so_to_ban_do" label="Số tờ bản đồ">
                    <Input placeholder="Vd: 12" />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={24}>
                  <Form.Item name="dia_chi_thua_dat" label="Địa chỉ thửa đất (Trên GCN)">
                    <TextArea rows={2} placeholder="Vị trí thửa đất theo GCN..." />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={24}>
                  <Form.Item name="owner_name" label="Chủ sở hữu cuối cùng (Người sử dụng đất)">
                    <Input placeholder="Tên chủ sở hữu..." />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={24}>
                  <Form.Item name="owner_address" label="Địa chỉ thường trú của chủ sở hữu">
                    <Input placeholder="Địa chỉ của chủ..." />
                  </Form.Item>
                </Col>
              </Row>
            </Collapse.Panel>
          </Collapse>

          {/* Section 4: Forwarding info */}
          <div style={{ backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8, padding: '12px 16px', marginBottom: 16 }}>
            <Form.Item name="professional_forward_enabled" valuePropName="checked" style={{ marginBottom: 8 }}>
              <Checkbox style={{ color: '#16a34a', fontWeight: 600 }}>Chuyển tiếp cho Nghiệp vụ khi Hành chính trả lời</Checkbox>
            </Form.Item>
            
            <Form.Item noStyle shouldUpdate={(prev, curr) => prev.professional_forward_enabled !== curr.professional_forward_enabled}>
              {({ getFieldValue }) => {
                const enabled = getFieldValue('professional_forward_enabled');
                return (
                  <Form.Item name="professional_recipient_email" label={<span style={{ color: '#16a34a', fontWeight: 600 }}>Người nhận Nghiệp vụ</span>} style={{ marginBottom: 0 }}>
                    <Select disabled={!enabled} style={{ width: '100%' }}>
                      <Option value="Kietna@cenvalue.vn">Kietna@cenvalue.vn</Option>
                      <Option value="anhvtn6@cenvalue.vn">anhvtn6@cenvalue.vn</Option>
                    </Select>
                  </Form.Item>
                );
              }}
            </Form.Item>
          </div>
        </div>

        {/* Footer Actions */}
        <div style={{ borderTop: '1px solid #e5e7eb', padding: '12px 0 4px 0', display: 'flex', flexWrap: 'wrap', gap: 12 }}>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={() => form.submit()}
            loading={saving}
            style={{ borderRadius: 6, flex: 1, minWidth: '110px' }}
          >
            Lưu SQLite
          </Button>

          <Button
            icon={<DownloadOutlined />}
            onClick={handleDownloadExcel}
            loading={downloading}
            style={{ borderRadius: 6, flex: 1, minWidth: '110px' }}
          >
            Xuất Excel
          </Button>

          <Button
            icon={<MailOutlined />}
            onClick={handleSendEmail}
            loading={sendingEmail}
            style={{ borderRadius: 6, flex: 1, minWidth: '110px' }}
          >
            Gửi mail
          </Button>

          <Button
            icon={<GlobalOutlined />}
            onClick={handleSubmitWeb}
            loading={submittingWeb}
            style={{ borderRadius: 6, flex: 1, minWidth: '110px' }}
          >
            Gửi Web
          </Button>
        </div>
      </Form>

      {/* Modal thêm mới Tổ chức */}
      <Modal
        open={newOrgModalOpen}
        title={
          <Space>
            <PlusOutlined style={{ color: '#007f7a' }} />
            <span>Thêm mới Tổ chức vào Danh bạ</span>
          </Space>
        }
        okText="Thêm"
        cancelText="Hủy"
        onCancel={() => { setNewOrgModalOpen(false); newOrgForm.resetFields(); }}
        onOk={() => newOrgForm.submit()}
        width={500}
        destroyOnClose
      >
        <Form
          form={newOrgForm}
          layout="vertical"
          onFinish={handleCreateOrgSubmit}
          style={{ marginTop: 16 }}
        >
          <Form.Item
            name="name"
            label="Tên công ty / tổ chức"
            rules={[{ required: true, message: 'Vui lòng nhập tên công ty' }]}
          >
            <Input placeholder="Ví dụ: Công ty TNHH MTV A" />
          </Form.Item>
          <Form.Item name="address" label="Địa chỉ công ty">
            <Input placeholder="Nhập địa chỉ..." />
          </Form.Item>
          <Form.Item name="tax_code" label="Mã số thuế">
            <Input placeholder="MST..." />
          </Form.Item>
          <Form.Item name="representative" label="Người đại diện pháp luật">
            <Input placeholder="Họ tên người đại diện..." />
          </Form.Item>
          <Form.Item name="position" label="Chức vụ người đại diện">
            <Input placeholder="Giám đốc, Chủ tịch..." />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
